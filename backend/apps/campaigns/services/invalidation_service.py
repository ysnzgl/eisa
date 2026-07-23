"""
Faz 4 — Invalidation Service

Domain değişikliği → etkilenen (kiosk_id, tarih) çifti → GenerationJob (queue).

Temel prensipler:
  - Signal handler'ları transaction.on_commit() ile job oluşturur.
  - Rollback olan domain değişikliği job üretmez.
  - Tek (kiosk, date) için PENDING job varken yeni oluşturulmaz (coalesce).
  - RUNNING varken yeni değişiklik kaybolmaz: yeni PENDING job eklenir.
  - Campaign.start/end dışına kalan tarihler için job üretilmez.
  - Geçmiş günler için job üretilmez (Europe/Istanbul bugününden itibaren).
  - Bu servis campaign sinyallerinden, Creative, DeliveryRule, HouseAd ve Kiosk
    sinyallerinden çağrılır.
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
    """Europe/Istanbul bugününden başlayan rolling horizon tarihleri.

    Default: DOOH_HORIZON_DAYS=3 → [today, today+1, today+2]
    """
    horizon = int(getattr(settings, "DOOH_HORIZON_DAYS", 3))
    today = datetime.now(_ISTANBUL_TZ).date()
    return [today + timedelta(days=i) for i in range(horizon)]


def enqueue_for_campaign(campaign, trigger_reason: str = "campaign_change") -> None:
    """Campaign değişikliği → etkilenen kiosk+tarih çiftleri için job oluştur.

    Yalnız horizon ile campaign tarih aralığının kesiştiği günler için job açılır.
    campaign.target_scope ve CampaignTarget'a göre kiosk çözümlemesi yapılır.
    """
    from apps.campaigns.services.placement_engine_v2 import _resolve_target_kiosks

    kiosk_ids = list(_resolve_target_kiosks(campaign))
    if not kiosk_ids:
        return

    horizon = get_horizon_dates()

    # Campaign tarih aralığı ile horizon'un kesişimi
    try:
        campaign_start = campaign.start_date.date() if hasattr(campaign.start_date, "date") else campaign.start_date
        campaign_end = campaign.end_date.date() if hasattr(campaign.end_date, "date") else campaign.end_date
        effective_dates = [d for d in horizon if campaign_start <= d <= campaign_end]
    except Exception:
        effective_dates = horizon  # Tarih ayrıştırma hatası → tümünü dene

    if not effective_dates:
        return

    enqueue_for_kiosk_dates(kiosk_ids, effective_dates, trigger_reason)


def enqueue_for_kiosk_dates(
    kiosk_ids: Iterable[int],
    dates: Iterable[date],
    trigger_reason: str,
) -> None:
    """Verilen kiosk+tarih çiftleri için job oluştur.

    Bu fonksiyon on_commit() callback'inden çağrılır (transaction commit edilmiş).
    """
    for kiosk_id in kiosk_ids:
        for d in dates:
            _create_or_coalesce_job(kiosk_id, d, trigger_reason)


def enqueue_for_all_kiosks(trigger_reason: str = "house_ad_change") -> None:
    """Tüm aktif kiosklar × horizon tarihleri için job oluştur.

    HouseAd değişikliği gibi global etkili değişiklikler için kullanılır.
    """
    from apps.pharmacies.models import Kiosk

    kiosk_ids = list(Kiosk.objects.filter(aktif=True).values_list("id", flat=True))
    enqueue_for_kiosk_dates(kiosk_ids, get_horizon_dates(), trigger_reason)


def enqueue_for_kiosk(kiosk_id: int, trigger_reason: str = "kiosk_change") -> None:
    """Tek kiosk için tüm horizon tarihleri için job oluştur.

    Yeni kiosk onayı veya kiosk aktiflik değişikliğinde kullanılır.
    """
    enqueue_for_kiosk_dates([kiosk_id], get_horizon_dates(), trigger_reason)


def _create_or_coalesce_job(
    kiosk_id: int,
    target_date: date,
    trigger_reason: str,
) -> Optional[object]:
    """Tek kiosk+tarih için job oluştur ya da mevcut PENDING ile birleştir.

    Coalescing mantığı:
    - PENDING + aynı dedupe_key → koalesce (yeni job açma)
    - RUNNING veya yok → yeni PENDING job aç
    - RETRY + aynı dedupe_key → koalesce (RETRY başlamadan önce PENDING yeterli)

    Bu şekilde aynı kiosk+tarih için gereksiz job üretilmez.
    RUNNING sırasında gelen yeni değişiklik kaybolmaz: RUNNING bittikten sonra
    işlenecek yeni PENDING job bırakılır.
    """
    from apps.campaigns.models import GenerationJob

    dedupe_key = f"kd:{kiosk_id}:{target_date}"

    # PENDING veya RETRY varsa koalesce et (zaten işleme alınacak)
    if GenerationJob.objects.filter(
        dedupe_key=dedupe_key,
        status__in=[GenerationJob.JobStatus.PENDING, GenerationJob.JobStatus.RETRY],
    ).exists():
        logger.debug(
            "InvalidationService: coalesced kiosk=%s date=%s reason=%s",
            kiosk_id,
            target_date,
            trigger_reason,
        )
        return None

    # Yeni PENDING job oluştur
    job = GenerationJob.objects.create(
        target_date=target_date,
        kiosk_id=kiosk_id,
        status=GenerationJob.JobStatus.PENDING,
        triggered_by=trigger_reason,
        dedupe_key=dedupe_key,
        payload={
            "kiosk_id": kiosk_id,
            "date": str(target_date),
            "trigger_reason": trigger_reason,
        },
        available_at=timezone.now(),
    )
    logger.debug(
        "InvalidationService: enqueued job=%s kiosk=%s date=%s reason=%s",
        job.pk,
        kiosk_id,
        target_date,
        trigger_reason,
    )
    return job
