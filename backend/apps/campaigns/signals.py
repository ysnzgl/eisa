"""Django sinyalleri — Campaign değişince ilgili kiosklarda playlist'i yeniden üret.

Scheduler process ayrı bir container'da çalışır. Sinyal, üretimi doğrudan
o process'e göndermek yerine **aynı process içinde thread'li** olarak tetikler.
Bu sayede hem web hem de scheduler container'ı birbirinden bağımsız kalır.

Tasarım kararı:
  ``regenerate_for_campaign`` fonksiyonu senkron çağrılırsa HTTP yanıt süresi uzar;
  bu nedenle ``threading.Thread`` ile arka planda çalıştırılır. Sonuç
  ``GenerationJob`` tablosuna yazılır, admin panel buradan okur.
"""
from __future__ import annotations

import logging
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Campaign

logger = logging.getLogger(__name__)

# Değişince yeniden üretimi tetikleyen alan adları
_TRIGGER_FIELDS = {"status", "start_date", "end_date", "name"}


@receiver(post_save, sender=Campaign)
def _on_campaign_save(sender, instance: Campaign, created: bool, update_fields=None, **kwargs):
    """Campaign kaydedilince etkilenen kiosklarda playlist'i yeniden üret.

    - Yeni kayıt (created=True) → her zaman tetikle
    - Güncelleme → yalnızca tetikleyici alan değiştiyse tetikle
    """
    if not created and update_fields is not None:
        changed = set(update_fields) & _TRIGGER_FIELDS
        if not changed:
            return

    def _run():
        from apps.campaigns.jobs import regenerate_for_campaign
        try:
            regenerate_for_campaign(str(instance.pk))
        except Exception:
            logger.exception(
                "Campaign post_save: regenerate_for_campaign başarısız campaign=%s",
                instance.pk,
            )

    t = threading.Thread(target=_run, daemon=True, name=f"regen-{instance.pk}")
    t.start()
    logger.info("Campaign %s kaydedildi; arka planda playlist yeniden üretimi başlatıldı.", instance.pk)
