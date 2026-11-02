"""APScheduler job fonksiyonlari — DOOH sponsorluk playlist uretimi.

``run_scheduler`` management command'i bu fonksiyonlari APScheduler'a kaydeder.

Jobs:
  nightly_generate   — Her gece: tum aktif kiosk x horizon icin PENDING job enqueue.
  mark_kiosks_offline — Ping gelmeyen kiosklari offline isaretle.
  drain_queue        — PENDING GenerationJob'lari tek motorla isle.
"""
from __future__ import annotations

import datetime as _dt
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def nightly_generate() -> None:
    """Horizon gunleri icin tum aktif kiosklara PENDING GenerationJob enqueue et."""
    from apps.campaigns.services.invalidation_service import (
        enqueue_for_all_kiosks,
    )

    enqueue_for_all_kiosks("nightly")
    logger.info("nightly_generate: tum aktif kiosklar x horizon enqueue edildi.")


def mark_kiosks_offline() -> None:
    """5 dakikadan fazla ping gondermeyen kvisklari offline isaretle."""
    from apps.pharmacies.models import Kiosk

    threshold = timezone.now() - _dt.timedelta(minutes=5)
    updated = Kiosk.objects.filter(
        aktif=True, son_goruldu__lt=threshold, is_online=True
    ).update(is_online=False)
    if updated:
        logger.info("mark_kiosks_offline: %d kiosk offline isaretlendi", updated)


def drain_queue(max_jobs: int = 20) -> None:
    """DB queue'yu bosalt: stale recovery + job claim + process."""
    from apps.campaigns.services.queue_worker import drain_queue as _drain

    processed = _drain(max_jobs=max_jobs)
    if processed:
        logger.info("drain_queue: %d job islendi", processed)
