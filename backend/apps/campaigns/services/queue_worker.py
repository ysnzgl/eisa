"""
Faz 4 — Queue Worker (Faz 7: flag-free canonical)

DB-backed job queue: claim, process, staged publish, retry, stale recovery.

Temel prensipler:
  - claim_next_job(): SELECT FOR UPDATE SKIP LOCKED → race-safe job sahiplenme.
  - process_job(): PlacementEngineV2 plan + fingerprint karşılaştırma + atomik publish.
  - recover_stale_jobs(): RUNNING + lock_expires_at geçmişse RETRY/FAILED.
  - drain_queue(): APScheduler/nightly tarafından çağrılan toplam döngü.
  - Faz 7: DOOH_ENGINE_V2 flag'i kaldırıldı; V2 publish her zaman aktif.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import date, timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.campaigns.models import GenerationJob, Playlist, PlaylistItem

logger = logging.getLogger(__name__)

_LEASE_SECONDS = 300  # 5 dakika per job
_MAX_BACKOFF_SECONDS = 300  # exponential backoff üst sınırı


def claim_next_job() -> Optional[GenerationJob]:
    """PENDING/RETRY job'ı race-safe şekilde sahiplen.

    SELECT FOR UPDATE SKIP LOCKED → iki worker aynı job'ı alamaz.
    İşlem atomic: claim + RUNNING durumuna geçiş tek transaction.
    """
    with transaction.atomic():
        job = (
            GenerationJob.objects.select_for_update(skip_locked=True)
            .filter(
                status__in=[
                    GenerationJob.JobStatus.PENDING,
                    GenerationJob.JobStatus.RETRY,
                ],
                available_at__lte=timezone.now(),
            )
            .order_by("available_at", "olusturulma_tarihi")
            .first()
        )
        if job is None:
            return None

        job.status = GenerationJob.JobStatus.RUNNING
        job.started_at = timezone.now()
        job.attempt_count += 1
        job.worker_id = f"pid-{os.getpid()}"
        job.lock_expires_at = timezone.now() + timedelta(seconds=_LEASE_SECONDS)
        job.save(update_fields=[
            "status", "started_at", "attempt_count",
            "worker_id", "lock_expires_at", "guncellenme_tarihi",
        ])
        return job


def process_job(job: GenerationJob) -> None:
    """Tek job'ı işle: plan + fingerprint karşılaştırma + staged publish.

    Hata durumunda eski playlist dokunulmaz kalır.
    """
    from apps.campaigns.services.placement_engine_v2 import PlacementEngineV2

    kiosk_id = job.kiosk_id
    target_date = job.target_date

    if kiosk_id is None:
        # Multi-kiosk nightly job (eski akış) → atla
        _complete_job(job, {"skipped": True, "reason": "multi_kiosk_job"}, version_bumped=False)
        return

    try:
        # 1. Plan (read-only)
        plan = PlacementEngineV2.plan_kiosk_day(
            kiosk_id=kiosk_id,
            target_date=target_date,
            planning_run=None,
        )
        new_fp = plan.fingerprint

        # Staged publish (V2 canonical — Faz 7)
        # Fingerprint karşılaştırması Kiosk row-lock altında yapılır.
        with transaction.atomic():
            from apps.campaigns.services.activation_service import ActivationService
            n_placements = ActivationService._persist_plan(
                kiosk_id, target_date, plan, check_fingerprint=True
            )

        if n_placements is None:
            # Fingerprint değişmemiş (lock altında doğrulandı) → yeniden üretme
            logger.debug(
                "QueueWorker: fingerprint unchanged (verified inside lock) kiosk=%s date=%s fp=%s",
                kiosk_id, target_date, new_fp,
            )
            _complete_job(
                job,
                {"fingerprint": new_fp, "version_bumped": False, "unchanged": True},
                version_bumped=False,
            )
            return

        logger.info(
            "QueueWorker: published kiosk=%s date=%s fp=%s placements=%s",
            kiosk_id, target_date, new_fp, n_placements,
        )
        _complete_job(
            job,
            {
                "fingerprint": new_fp,
                "version_bumped": True,
                "placements": n_placements,
            },
            version_bumped=True,
        )

    except Exception as exc:
        _handle_failure(job, exc)


def recover_stale_jobs() -> int:
    """Lease süresi dolan RUNNING job'ları RETRY/FAILED'a çevir.

    Stale: lock_expires_at < now → worker process çökmüş olabilir.
    İki worker aynı anda aynı job'ı sahiplenmez: lock_expires_at kontrolü atomik değil
    ama claim_next_job SELECT FOR UPDATE ile korunduğundan double-claim olmaz.
    """
    now = timezone.now()
    stale = list(
        GenerationJob.objects.filter(
            status=GenerationJob.JobStatus.RUNNING,
            lock_expires_at__lt=now,
        )
    )

    recovered = 0
    for job in stale:
        if job.attempt_count >= job.max_attempts:
            job.status = GenerationJob.JobStatus.FAILED
            job.error_detail = (
                f"Maksimum deneme sayısı aşıldı ({job.attempt_count}/{job.max_attempts}). "
                f"Stale recovery: lock_expires_at={job.lock_expires_at}"
            )
            job.finished_at = now
        else:
            # Exponential backoff: 30s, 60s, 120s, ... max 300s
            backoff = min(30 * (2 ** (job.attempt_count - 1)), _MAX_BACKOFF_SECONDS)
            job.status = GenerationJob.JobStatus.RETRY
            job.available_at = now + timedelta(seconds=backoff)
            job.worker_id = None
            job.lock_expires_at = None
            job.error_detail = (
                f"Stale recovery: attempt={job.attempt_count}. "
                f"Retry after {backoff}s."
            )
        job.save(update_fields=[
            "status", "available_at", "worker_id", "lock_expires_at",
            "error_detail", "finished_at", "guncellenme_tarihi",
        ])
        recovered += 1
        logger.warning(
            "QueueWorker: stale job recovered job=%s new_status=%s",
            job.pk, job.status,
        )

    return recovered


def drain_queue(max_jobs: int = 20) -> int:
    """APScheduler/nightly worker döngüsü.

    Önce stale job'ları kurtar, sonra max_jobs kadar job işle.
    Dönen değer: işlenen job sayısı.
    """
    recover_stale_jobs()

    processed = 0
    while processed < max_jobs:
        job = claim_next_job()
        if job is None:
            break
        try:
            process_job(job)
        except Exception as exc:
            logger.exception("QueueWorker.drain_queue: unhandled exception job=%s: %s", job.pk, exc)
            _handle_failure(job, exc)
        processed += 1

    return processed


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _get_current_fingerprint(kiosk_id: int, target_date: date) -> Optional[str]:
    """Mevcut authoritative fingerprint'i gerçek PlaylistItem içeriğinden hesapla.

    Circular import önlemek için ActivationService._compute_playlist_fingerprint delegated.
    """
    from apps.campaigns.services.activation_service import ActivationService
    return ActivationService._compute_playlist_fingerprint(kiosk_id, target_date)


def _complete_job(
    job: GenerationJob,
    result_payload: dict,
    version_bumped: bool,
) -> None:
    """Job'ı DONE durumuna geçir ve sonucu payload'a kaydet."""
    now = timezone.now()
    merged_payload = {**job.payload, **result_payload}
    GenerationJob.objects.filter(pk=job.pk).update(
        status=GenerationJob.JobStatus.DONE,
        finished_at=now,
        playlists_generated=result_payload.get("placements", 0),
        done_kiosks=1 if not result_payload.get("skipped") else 0,
        payload=merged_payload,
    )


def _handle_failure(job: GenerationJob, exc: Exception) -> None:
    """Hata durumunda job'ı RETRY veya FAILED'a çevir."""
    # Hata detayını sanitize et (stack trace hariç sadece type+message)
    error_msg = f"{type(exc).__name__}: {str(exc)[:256]}"
    logger.warning("QueueWorker: job failed job=%s: %s", job.pk, error_msg)

    now = timezone.now()

    if job.attempt_count < job.max_attempts:
        backoff = min(30 * (2 ** (job.attempt_count - 1)), _MAX_BACKOFF_SECONDS)
        GenerationJob.objects.filter(pk=job.pk).update(
            status=GenerationJob.JobStatus.RETRY,
            available_at=now + timedelta(seconds=backoff),
            worker_id=None,
            lock_expires_at=None,
            error_detail=error_msg,
        )
    else:
        GenerationJob.objects.filter(pk=job.pk).update(
            status=GenerationJob.JobStatus.FAILED,
            finished_at=now,
            failed_kiosks=1,
            error_detail=error_msg,
        )
