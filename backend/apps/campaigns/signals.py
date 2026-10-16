"""Django sinyalleri — sponsorluk degisikliklerinden etkilenen kiosklarda playlist uret.

Tum domain degisiklikleri transaction.on_commit() + invalidation_service ile
GenerationJob queue'ya alinir. Etkilenen kiosklar: ilgili kampanyaya atanmis
(KioskSponsorship) kiosklar. Yeni/aktive kiosk -> yalniz kendi kiosk'u (atama yoksa
bos program uretir).
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from .models import Campaign, Creative, KioskSponsorship

logger = logging.getLogger(__name__)

# Campaign degisikliklerinde planlamayi etkileyen alanlar
_CAMPAIGN_TRIGGER_FIELDS = {"status", "start_date", "end_date"}
# Creative degisikliklerinde planlamayi etkileyen alanlar
_CREATIVE_TRIGGER_FIELDS = {
    "duration_seconds", "media_url", "object_key", "checksum",
    "active_media_url", "active_object_key",
}


def _enqueue_campaign(campaign_id, trigger_reason: str) -> None:
    from apps.campaigns.services.invalidation_service import enqueue_for_campaign

    transaction.on_commit(lambda: enqueue_for_campaign(campaign_id, trigger_reason))


# ── Campaign ──────────────────────────────────────────────────────────────────


@receiver(post_save, sender=Campaign)
def _on_campaign_save(sender, instance: Campaign, created: bool, update_fields=None, **kwargs) -> None:
    if not created and update_fields is not None:
        if not (set(update_fields) & _CAMPAIGN_TRIGGER_FIELDS):
            return
    _enqueue_campaign(instance.id, "campaign_create" if created else "campaign_change")


@receiver(pre_delete, sender=Campaign)
def _on_campaign_pre_delete(sender, instance: Campaign, **kwargs) -> None:
    from apps.campaigns.services.invalidation_service import (
        get_horizon_dates, enqueue_for_kiosk_dates,
    )

    kiosk_ids = list(instance.kiosk_sponsorships.values_list("kiosk_id", flat=True))
    dates = get_horizon_dates()
    transaction.on_commit(lambda: enqueue_for_kiosk_dates(kiosk_ids, dates, "campaign_delete"))


# ── Creative ──────────────────────────────────────────────────────────────────


@receiver(post_save, sender=Creative)
def _on_creative_save(sender, instance: Creative, created: bool, update_fields=None, **kwargs) -> None:
    if not created and update_fields is not None:
        if not (set(update_fields) & _CREATIVE_TRIGGER_FIELDS):
            return
    _enqueue_campaign(instance.campaign_id, "creative_create" if created else "creative_change")


@receiver(pre_delete, sender=Creative)
def _on_creative_pre_delete(sender, instance: Creative, **kwargs) -> None:
    _enqueue_campaign(instance.campaign_id, "creative_delete")


# ── KioskSponsorship ───────────────────────────────────────────────────────────


@receiver(post_save, sender=KioskSponsorship)
def _on_sponsorship_save(sender, instance: KioskSponsorship, created: bool, **kwargs) -> None:
    from apps.campaigns.services.invalidation_service import enqueue_for_kiosk

    kiosk_id = instance.kiosk_id
    transaction.on_commit(lambda: enqueue_for_kiosk(kiosk_id, "sponsorship_change"))


@receiver(post_delete, sender=KioskSponsorship)
def _on_sponsorship_delete(sender, instance: KioskSponsorship, **kwargs) -> None:
    from apps.campaigns.services.invalidation_service import enqueue_for_kiosk

    kiosk_id = instance.kiosk_id
    transaction.on_commit(lambda: enqueue_for_kiosk(kiosk_id, "sponsorship_delete"))


# ── Kiosk — yeni kiosk veya aktiflik degisikligi ────────────────────────────────

_KIOSK_TRIGGER_FIELDS = {"aktif"}


@receiver(post_save, sender="pharmacies.Kiosk")
def _on_kiosk_save(sender, instance, created: bool, update_fields=None, **kwargs) -> None:
    """Yeni kiosk veya aktiflik degisikligi -> kiosk invalidation (opt-in: atama yoksa bos)."""
    if not created and update_fields is not None:
        if not (set(update_fields) & _KIOSK_TRIGGER_FIELDS):
            return
    if not instance.aktif:
        return
    from apps.campaigns.services.invalidation_service import enqueue_for_kiosk

    kiosk_id = instance.id
    transaction.on_commit(lambda: enqueue_for_kiosk(
        kiosk_id, "kiosk_activate" if created else "kiosk_change"
    ))
