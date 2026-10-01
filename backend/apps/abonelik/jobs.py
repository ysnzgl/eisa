"""APScheduler job fonksiyonları — abonelik faturalandırma otomasyonu.

``run_scheduler`` management command'ı bu fonksiyonları kaydeder. Tüm işler
idempotenttir; günde bir kez çalışacak şekilde tasarlanmıştır ama aynı gün
birden çok kez tetiklense de mükerrer fatura üretmez.

Jobs:
  gunluk_faturalandirma — Kullanım bedeli + cihaz taksiti + cihaz kira üretir, gecikmişleri işaretler.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def gunluk_faturalandirma() -> None:
    """Günlük abonelik faturalandırma döngüsü.

    1) Aktif sözleşmeler için içinde bulunulan dönemin kullanım bedelini üret
       (öteleme dönemi ve sözleşme bitişi dikkate alınır).
    2) Ayın ilk haftasında cihaz taksitlerini üret.
    3) Vadesi + grace süresi geçmiş faturaları GECIKTI yap.
    """
    from apps.abonelik.services import (
        faturala_cihaz_kira,
        faturala_cihaz_taksit,
        faturala_kullanim_bedeli,
        guncelle_gecikmis_faturalar,
    )

    kullanim = faturala_kullanim_bedeli()
    cihaz = faturala_cihaz_taksit()
    kira = faturala_cihaz_kira()
    gecikmis = guncelle_gecikmis_faturalar()
    logger.info(
        "gunluk_faturalandirma tamamlandı: kullanim=%d cihaz=%d kira=%d gecikmis=%d",
        kullanim, cihaz, kira, gecikmis,
    )
