"""Django sinyalleri â€” Domain deÄŸiÅŸikliklerinden etkilenen kiosklarda playlist'i yeniden Ã¼ret.

Faz 7: DOOH_ASYNC_QUEUE kaldÄ±rÄ±ldÄ±; async DB queue her zaman aktif.
  - TÃ¼m domain deÄŸiÅŸiklikleri transaction.on_commit() + InvalidationService ile queue'ya alÄ±nÄ±r.
  - Legacy thread (DOOH_ASYNC_QUEUE=False) yolu kaldÄ±rÄ±ldÄ±.

Faz 5 eklentileri:
  - Kiosk.eczane_id deÄŸiÅŸince hem eski hem yeni eczane'nin campaign'leri invalidate edilir.
  - Eczane.il_id / ilce_id / aktif deÄŸiÅŸince eczanedeki kiosklara horizon invalidation.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from .models import Campaign, Creative, DeliveryRule, HouseAd
from .models import CampaignTarget

logger = logging.getLogger(__name__)

# Campaign deÄŸiÅŸikliklerinde planlamayÄ± etkileyen alanlar
_CAMPAIGN_TRIGGER_FIELDS = {
    "status", "start_date", "end_date", "priority",
    "target_scope", "follows_id",
}
# Creative deÄŸiÅŸikliklerinde planlamayÄ± etkileyen alanlar
_CREATIVE_TRIGGER_FIELDS = {
    "duration_seconds", "media_url", "object_key", "checksum", "weight", "aktif",
}


def _should_skip_campaign(created: bool, update_fields) -> bool:
    """Gereksiz invalidation tetikleme kontrolÃ¼."""
    if created:
        return False  # yeni kayÄ±t â†’ her zaman tetikle
    if update_fields is None:
        return False  # tÃ¼m alanlar gÃ¼ncellendi â†’ tetikle
    return not (set(update_fields) & _CAMPAIGN_TRIGGER_FIELDS)


def _enqueue_campaign_async(campaign, trigger_reason: str) -> None:
    """on_commit + InvalidationService (queue mode)."""
    from apps.campaigns.services.invalidation_service import enqueue_for_campaign

    transaction.on_commit(lambda: enqueue_for_campaign(campaign, trigger_reason))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Campaign signals
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@receiver(post_save, sender=Campaign)
def _on_campaign_save(
    sender, instance: Campaign, created: bool, update_fields=None, **kwargs
) -> None:
    """Campaign kaydedilince etkilenen kiosklarda playlist'i yeniden Ã¼ret."""
    if _should_skip_campaign(created, update_fields):
        return

    _enqueue_campaign_async(instance, "campaign_change" if not created else "campaign_create")


@receiver(pre_delete, sender=Campaign)
def _on_campaign_pre_delete(sender, instance: Campaign, **kwargs) -> None:
    """Campaign silinmeden Ã¶nce etkilenen kiosk ID'lerini capture et.

    Silme sonrasÄ± FK iliÅŸkileri kaybolacaÄŸÄ±ndan kiosk Ã§Ã¶zÃ¼mlemesi burada yapÄ±lÄ±r.
    """
    from apps.campaigns.services.placement_engine_v2 import _resolve_target_kiosks
    from apps.campaigns.services.invalidation_service import (
        get_horizon_dates,
        enqueue_for_kiosk_dates,
    )

    try:
        kiosk_ids = list(_resolve_target_kiosks(instance))
        dates = get_horizon_dates()
    except Exception:
        logger.exception("_on_campaign_pre_delete: kiosk Ã§Ã¶zÃ¼mlemesi baÅŸarÄ±sÄ±z campaign=%s", instance.pk)
        return

    transaction.on_commit(lambda: enqueue_for_kiosk_dates(kiosk_ids, dates, "campaign_delete"))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Creative signals
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@receiver(post_save, sender=Creative)
def _on_creative_save(
    sender, instance: Creative, created: bool, update_fields=None, **kwargs
) -> None:
    """Creative deÄŸiÅŸikliÄŸi â†’ kampanyanÄ±n kiosk+tarihlerini invalidate et."""
    if not created and update_fields is not None:
        if not (set(update_fields) & _CREATIVE_TRIGGER_FIELDS):
            return

    _enqueue_campaign_async(instance.campaign, "creative_change" if not created else "creative_create")


@receiver(pre_delete, sender=Creative)
def _on_creative_pre_delete(sender, instance: Creative, **kwargs) -> None:
    """Creative silinmeden Ã¶nce campaign kiosk kapsamÄ±nÄ± capture et."""
    from apps.campaigns.services.invalidation_service import enqueue_for_campaign
    campaign = instance.campaign
    transaction.on_commit(lambda: enqueue_for_campaign(campaign, "creative_delete"))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# DeliveryRule signals
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@receiver(post_save, sender=DeliveryRule)
def _on_delivery_rule_save(
    sender, instance: DeliveryRule, created: bool, **kwargs
) -> None:
    """DeliveryRule deÄŸiÅŸikliÄŸi â†’ kampanya invalidation."""

    _enqueue_campaign_async(instance.campaign, "delivery_rule_change")


@receiver(post_delete, sender=DeliveryRule)
def _on_delivery_rule_delete(sender, instance: DeliveryRule, **kwargs) -> None:

    from apps.campaigns.services.invalidation_service import enqueue_for_campaign
    campaign = instance.campaign
    transaction.on_commit(lambda: enqueue_for_campaign(campaign, "delivery_rule_delete"))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CampaignTarget signals
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@receiver(post_save, sender=CampaignTarget)
def _on_campaign_target_save(
    sender, instance: CampaignTarget, created: bool, **kwargs
) -> None:
    """CampaignTarget deÄŸiÅŸikliÄŸi â†’ kampanya invalidation."""

    _enqueue_campaign_async(instance.campaign, "target_change")


@receiver(post_delete, sender=CampaignTarget)
def _on_campaign_target_delete(sender, instance: CampaignTarget, **kwargs) -> None:

    from apps.campaigns.services.invalidation_service import enqueue_for_campaign
    campaign = instance.campaign
    transaction.on_commit(lambda: enqueue_for_campaign(campaign, "target_delete"))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# HouseAd signals â€” tÃ¼m kiosklar etkilenir
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@receiver(post_save, sender=HouseAd)
def _on_house_ad_save(sender, instance: HouseAd, created: bool, **kwargs) -> None:
    """HouseAd deÄŸiÅŸikliÄŸi â†’ tÃ¼m aktif kiosklar Ã— horizon invalidation."""

    from apps.campaigns.services.invalidation_service import enqueue_for_all_kiosks
    transaction.on_commit(lambda: enqueue_for_all_kiosks("house_ad_change"))


@receiver(post_delete, sender=HouseAd)
def _on_house_ad_delete(sender, instance: HouseAd, **kwargs) -> None:

    from apps.campaigns.services.invalidation_service import enqueue_for_all_kiosks
    transaction.on_commit(lambda: enqueue_for_all_kiosks("house_ad_delete"))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Kiosk signals â€” yeni kiosk veya aktiflik deÄŸiÅŸikliÄŸi
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_KIOSK_TRIGGER_FIELDS = {"aktif", "eczane_id"}


@receiver(pre_save, sender="pharmacies.Kiosk")
def _on_kiosk_pre_save(sender, instance, **kwargs) -> None:
    """Kiosk eczane deÄŸiÅŸikliÄŸinde eski eczane kapsamÄ±nÄ± capture et.

    Silme gibi: kiosk baÅŸka eczaneye taÅŸÄ±nÄ±rsa eski eczane'nin kampanya hedeflemesi
    deÄŸiÅŸir. pre_save'de eski eczane_id kayÄ±t altÄ±na alÄ±nÄ±r.
    """
    if instance.pk:
        try:
            from apps.pharmacies.models import Kiosk as _Kiosk
            old = _Kiosk.objects.only("eczane_id", "aktif").get(pk=instance.pk)
            instance._old_eczane_id = old.eczane_id
            instance._was_aktif = old.aktif
        except Exception:
            pass  # Yeni kayÄ±t veya DB hatasÄ± â†’ capture edilmez


@receiver(post_save, sender="pharmacies.Kiosk")
def _on_kiosk_save(
    sender, instance, created: bool, update_fields=None, **kwargs
) -> None:
    """Yeni kiosk veya aktiflik/eczane deÄŸiÅŸikliÄŸi â†’ kiosk invalidation.

    Faz 5 fix: Kiosk eczane deÄŸiÅŸimi hem eski hem yeni kapsamÄ± invalidate eder.
    """

    if not created and update_fields is not None:
        if not (set(update_fields) & _KIOSK_TRIGGER_FIELDS):
            return

    from apps.campaigns.services.invalidation_service import (
        enqueue_for_kiosk,
        enqueue_for_kiosk_dates,
        get_horizon_dates,
    )
    from apps.pharmacies.models import Kiosk as _Kiosk

    kiosk_id = instance.id
    old_eczane_id = getattr(instance, "_old_eczane_id", None)
    eczane_changed = (old_eczane_id is not None and old_eczane_id != instance.eczane_id)

    if eczane_changed:
        # Eski eczane'nin kampanyalarÄ± artÄ±k bu kiosk'u hedeflemeyebilir
        # â†’ o eczanedeki kalan kiosklara da horizon invalidation
        old_eczane = old_eczane_id  # capture for closure
        def _enqueue_eczane_change():
            try:
                old_kiosks = list(
                    _Kiosk.objects.filter(eczane_id=old_eczane, aktif=True)
                    .values_list("id", flat=True)
                )
                dates = get_horizon_dates()
                if old_kiosks:
                    enqueue_for_kiosk_dates(old_kiosks, dates, "kiosk_eczane_change_old")
                # Yeni eczane
                enqueue_for_kiosk(kiosk_id, "kiosk_eczane_change_new")
            except Exception:
                logger.exception("_on_kiosk_save: eczane deÄŸiÅŸikliÄŸi invalidation baÅŸarÄ±sÄ±z kiosk=%s", kiosk_id)

        transaction.on_commit(_enqueue_eczane_change)
    elif instance.aktif:
        transaction.on_commit(lambda: enqueue_for_kiosk(
            kiosk_id, "kiosk_activate" if created else "kiosk_change"
        ))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Eczane signals â€” il/ilÃ§e/aktiflik deÄŸiÅŸimi kiosklarÄ±nÄ± etkiler
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_ECZANE_TRIGGER_FIELDS = {"il_id", "ilce_id", "aktif"}


@receiver(post_save, sender="pharmacies.Eczane")
def _on_eczane_save(
    sender, instance, created: bool, update_fields=None, **kwargs
) -> None:
    """Eczane il/ilÃ§e/aktiflik deÄŸiÅŸikliÄŸi â†’ eczanedeki kiosklara horizon invalidation.

    Senaryo: Eczane Ä°stanbul KadÄ±kÃ¶y'den Ä°stanbul BeÅŸiktaÅŸ'a taÅŸÄ±ndÄ±.
    IL/ILCE hedefli kampanyalarÄ±n hedef kapsamÄ± deÄŸiÅŸmiÅŸ olabilir.
    """

    if not created and update_fields is not None:
        if not (set(update_fields) & _ECZANE_TRIGGER_FIELDS):
            return

    eczane_id = instance.pk

    def _enqueue():
        try:
            from apps.pharmacies.models import Kiosk as _Kiosk
            from apps.campaigns.services.invalidation_service import (
                enqueue_for_kiosk_dates,
                get_horizon_dates,
            )
            kiosk_ids = list(
                _Kiosk.objects.filter(eczane_id=eczane_id, aktif=True)
                .values_list("id", flat=True)
            )
            if kiosk_ids:
                enqueue_for_kiosk_dates(kiosk_ids, get_horizon_dates(), "eczane_change")
        except Exception:
            logger.exception("_on_eczane_save: invalidation baÅŸarÄ±sÄ±z eczane=%s", eczane_id)

    transaction.on_commit(_enqueue)
