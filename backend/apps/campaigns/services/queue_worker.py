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
    """Tek job'ı işle: V1 loop-filler ile playlist üret (kanonik).

    Kanonik playlist üretimi 24 saatin tamamını doğru dolduran V1
    ``generate_for_kiosk`` iledir (nightly job ile aynı motor). V2
    ``PlacementEngineV2`` yalnız kapasite simülasyonu içindir; 24 saatlik
    dağıtımı yapmaz. Hata durumunda eski playlist dokunulmaz kalır.
    """
    kiosk_id = job.kiosk_id
    target_date = job.target_date

    if kiosk_id is None:
        # Multi-kiosk nightly job (eski akış) → atla
        _complete_job(job, {"skipped": True, "reason": "multi_kiosk_job"}, version_bumped=False)
        return

    try:
        n_placements = regenerate_kiosk_day(kiosk_id, target_date)

        if n_placements is None:
            # İçerik değişmemiş (deterministik seed) → versiyon artırma
            logger.debug(
                "QueueWorker: content unchanged kiosk=%s date=%s → no version bump",
                kiosk_id, target_date,
            )
            _complete_job(
                job,
                {"version_bumped": False, "unchanged": True},
                version_bumped=False,
            )
            return

        logger.info(
            "QueueWorker: published (V1) kiosk=%s date=%s placements=%s",
            kiosk_id, target_date, n_placements,
        )
        _complete_job(
            job,
            {"version_bumped": True, "placements": n_placements},
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


def regenerate_kiosk_day(kiosk_id: int, target_date: date) -> Optional[int]:
    """Bir kiosk-gün için playlist'i V1 loop-filler motoruyla (yeniden) üret.

    V1 ``generate_for_kiosk`` 24 saatin tamamını doğru dolduran kanonik
    üreticidir (nightly job ile aynı) ve ``Kiosk.last_playlist_version``'ı
    günceller → kiosk yeni playlist'i çeker.

    İçerik değişmediyse (deterministik seed) gereksiz versiyon artışını ve
    kiosk ACK dalgalanmasını önlemek için üretim geri alınır.

    Returns:
        Üretilen creative item sayısı; içerik değişmediyse None.
    """
    from apps.campaigns.services.scheduler import generate_for_kiosk
    from apps.pharmacies.models import Kiosk

    try:
        kiosk = Kiosk.objects.get(pk=kiosk_id, aktif=True)
    except Kiosk.DoesNotExist:
        return None

    before_fp = _get_current_fingerprint(kiosk_id, target_date)

    unchanged = False
    creative_count = 0
    with transaction.atomic():
        playlists = generate_for_kiosk(kiosk, target_date)
        creative_count = sum(
            p.items.filter(creative__isnull=False).count() for p in playlists
        )
        after_fp = _get_current_fingerprint(kiosk_id, target_date)
        if before_fp is not None and before_fp == after_fp:
            unchanged = True
            transaction.set_rollback(True)

    if unchanged:
        # İçerik aynı → üretim geri alındı. Yine de desired versiyonu mevcut
        # içerikle eşitle (eski/hatalı üretimlerden kalan desync'i onar).
        _sync_kiosk_desired_version(kiosk_id)
        return None
    return creative_count


def _sync_kiosk_desired_version(kiosk_id: int) -> None:
    """Kiosk.last_playlist_version'ı mevcut en yüksek Playlist versiyonuna hizala.

    Yalnız geride ise günceller (churn yok). İçerik değişmediği hâlde desired
    versiyon geride kalmışsa kiosk'un pull tetiklemesini sağlar.
    """
    from django.db.models import Max, Q
    from apps.campaigns.models import Playlist
    from apps.pharmacies.models import Kiosk

    max_v = Playlist.objects.filter(kiosk_id=kiosk_id).aggregate(mv=Max("version"))["mv"] or 0
    if max_v:
        Kiosk.objects.filter(pk=kiosk_id).filter(
            Q(last_playlist_version__isnull=True) | Q(last_playlist_version__lt=max_v)
        ).update(last_playlist_version=max_v)


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
