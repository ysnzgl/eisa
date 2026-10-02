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
        faturala_aylik_birlesik,
        guncelle_gecikmis_faturalar,
    )

    yeni = faturala_aylik_birlesik()
    gecikmis = guncelle_gecikmis_faturalar()
    logger.info(
        "gunluk_faturalandirma tamamlandı: birlesik=%d gecikmis=%d",
        yeni, gecikmis,
    )
