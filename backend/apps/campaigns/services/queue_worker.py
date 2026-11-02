"""Queue Worker — DB-backed job queue: claim, process, retry, stale recovery.

Her job (kiosk, date) icin tek yerlesim motorunu (sponsorship_engine) calistirir.
"""
from __future__ import annotations

import logging
import os
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from apps.campaigns.models import GenerationJob

logger = logging.getLogger(__name__)

_LEASE_SECONDS = 300
_MAX_BACKOFF_SECONDS = 300


def claim_next_job() -> Optional[GenerationJob]:
    """PENDING/RETRY job'i race-safe sekilde sahiplen (SELECT FOR UPDATE SKIP LOCKED)."""
    with transaction.atomic():
        job = (
            GenerationJob.objects.select_for_update(skip_locked=True)
            .filter(
                status__in=[GenerationJob.JobStatus.PENDING, GenerationJob.JobStatus.RETRY],
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
    """Tek job'i isle: (kiosk, date) icin plan + kalicilastir."""
    from apps.campaigns.services.sponsorship_engine import regenerate_kiosk_day

    kiosk_id = job.kiosk_id
    target_date = job.target_date

    if kiosk_id is None:
        _complete_job(job, {"skipped": True, "reason": "multi_kiosk_job"}, version_bumped=False)
        return

    try:
        n = regenerate_kiosk_day(kiosk_id, target_date)
        if n is None:
            _complete_job(job, {"version_bumped": False, "unchanged": True}, version_bumped=False)
            return
        _complete_job(job, {"version_bumped": True, "placements": n}, version_bumped=True)
    except Exception as exc:
        _handle_failure(job, exc)


def recover_stale_jobs() -> int:
    """Lease suresi dolan RUNNING job'lari RETRY/FAILED'a cevir."""
    now = timezone.now()
    stale = list(
        GenerationJob.objects.filter(
            status=GenerationJob.JobStatus.RUNNING, lock_expires_at__lt=now
        )
    )
    recovered = 0
    for job in stale:
        if job.attempt_count >= job.max_attempts:
            job.status = GenerationJob.JobStatus.FAILED
            job.error_detail = f"Maksimum deneme sayisi asildi ({job.attempt_count}/{job.max_attempts})."
            job.finished_at = now
        else:
            backoff = min(30 * (2 ** (job.attempt_count - 1)), _MAX_BACKOFF_SECONDS)
            job.status = GenerationJob.JobStatus.RETRY
            job.available_at = now + timedelta(seconds=backoff)
            job.worker_id = None
            job.lock_expires_at = None
            job.error_detail = f"Stale recovery: attempt={job.attempt_count}. Retry after {backoff}s."
        job.save(update_fields=[
            "status", "available_at", "worker_id", "lock_expires_at",
            "error_detail", "finished_at", "guncellenme_tarihi",
        ])
        recovered += 1
    return recovered


def drain_queue(max_jobs: int = 20) -> int:
    """APScheduler/nightly worker dongusu: stale recovery + max_jobs job isle."""
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


# ── Helpers ─────────────────────────────────────────────────────────────────


def _complete_job(job: GenerationJob, result_payload: dict, version_bumped: bool) -> None:
    now = timezone.now()
    merged_payload = {**(job.payload or {}), **result_payload}
    GenerationJob.objects.filter(pk=job.pk).update(
        status=GenerationJob.JobStatus.DONE,
        finished_at=now,
        playlists_generated=result_payload.get("placements", 0),
        done_kiosks=1 if not result_payload.get("skipped") else 0,
        payload=merged_payload,
    )


def _handle_failure(job: GenerationJob, exc: Exception) -> None:
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
