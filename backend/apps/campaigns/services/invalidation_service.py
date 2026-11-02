"""Invalidation Service — domain degisikligi -> (kiosk, tarih) -> GenerationJob queue.

Temel prensipler:
  - Signal handler'lari transaction.on_commit() ile job olusturur.
  - Tek (kiosk, date) icin PENDING/RETRY job varken yeni olusturulmaz (coalesce).
  - Gecmis gunler icin job uretilmez (Europe/Istanbul bugununden itibaren).
  - Etkilenen kiosklar: ilgili kampanyaya atanmis (KioskSponsorship) kiosklar.
"""
from __future__ import annotations

import logging
import zoneinfo
from datetime import date, datetime, timedelta
from typing import Iterable, List, Optional

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

_ISTANBUL_TZ = zoneinfo.ZoneInfo("Europe/Istanbul")


def get_horizon_dates() -> List[date]:
    """Europe/Istanbul bugununden baslayan rolling horizon tarihleri (DOOH_HORIZON_DAYS)."""
    horizon = int(getattr(settings, "DOOH_HORIZON_DAYS", 3))
    today = datetime.now(_ISTANBUL_TZ).date()
    return [today + timedelta(days=i) for i in range(horizon)]


def _resolve_campaign_kiosks(campaign_id) -> List[int]:
    from apps.campaigns.models import KioskSponsorship

    return list(
        KioskSponsorship.objects
        .filter(campaign_id=campaign_id, kiosk__aktif=True)
        .values_list("kiosk_id", flat=True)
        .distinct()
    )


def enqueue_for_campaign(campaign_id, trigger_reason: str = "campaign_change") -> None:
    """Kampanya degisikligi -> atanmis kiosklar x horizon icin job olustur."""
    kiosk_ids = _resolve_campaign_kiosks(campaign_id)
    if not kiosk_ids:
        return
    enqueue_for_kiosk_dates(kiosk_ids, get_horizon_dates(), trigger_reason)


def enqueue_for_kiosk_dates(
    kiosk_ids: Iterable[int], dates: Iterable[date], trigger_reason: str
) -> None:
    dates = list(dates)
    for kiosk_id in kiosk_ids:
        for d in dates:
            _create_or_coalesce_job(kiosk_id, d, trigger_reason)


def enqueue_for_all_kiosks(trigger_reason: str = "global_change") -> None:
    from apps.pharmacies.models import Kiosk

    kiosk_ids = list(Kiosk.objects.filter(aktif=True).values_list("id", flat=True))
    enqueue_for_kiosk_dates(kiosk_ids, get_horizon_dates(), trigger_reason)


def enqueue_for_kiosk(kiosk_id: int, trigger_reason: str = "kiosk_change") -> None:
    enqueue_for_kiosk_dates([kiosk_id], get_horizon_dates(), trigger_reason)


def _create_or_coalesce_job(kiosk_id: int, target_date: date, trigger_reason: str) -> Optional[object]:
    """Tek kiosk+tarih icin job olustur ya da mevcut PENDING/RETRY ile birlestir."""
    from apps.campaigns.models import GenerationJob

    dedupe_key = f"kd:{kiosk_id}:{target_date}"

    if GenerationJob.objects.filter(
        dedupe_key=dedupe_key,
        status__in=[GenerationJob.JobStatus.PENDING, GenerationJob.JobStatus.RETRY],
    ).exists():
        return None

    job = GenerationJob.objects.create(
        target_date=target_date,
        kiosk_id=kiosk_id,
        status=GenerationJob.JobStatus.PENDING,
        triggered_by=trigger_reason,
        dedupe_key=dedupe_key,
        payload={"kiosk_id": kiosk_id, "date": str(target_date), "trigger_reason": trigger_reason},
        available_at=timezone.now(),
    )
    return job
