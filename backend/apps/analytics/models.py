"""Anonim demografik ve davranissal log modelleri (KVKK uyumlu)."""
import uuid

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class OturumLogu(BaseModel):
    """Bir kiosk oturumu — kisiyi tanimlayan hicbir veri ICERMEZ."""

    # Kioskun urettigi duplicate-koruma anahtari (SEC-004 / ARC-001).
    idempotency_anahtari = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="oturumlar"
    )
    yas_araligi = models.ForeignKey(
        "lookups.YasAraligi", on_delete=models.PROTECT, related_name="oturumlar"
    )
    cinsiyet = models.ForeignKey(
        "lookups.Cinsiyet", on_delete=models.PROTECT, related_name="oturumlar"
    )
    kategori = models.ForeignKey(
        "products.Kategori", on_delete=models.PROTECT, related_name="oturumlar"
    )
    hassas_akis = models.BooleanField(default=False)
    qr_kodu = models.CharField(max_length=64, db_index=True)
    cevaplar = models.JSONField(default=dict, blank=True)
    onerilen_etken_maddeler = models.JSONField(default=list, blank=True)
    tamamlandi = models.BooleanField(
        default=True,
        help_text=(
            "True = kullanici akisi tamamladi (QR uretildi). "
            "False = 10sn etkilesimsizlik ile terk edilmis (sahte/abandoned oturum)."
        ),
    )

    # Eczacı danışma tamamlama akışı
    danisma_tamamlandi = models.BooleanField(default=False, db_index=True)
    danisma_tamamlanma_tarihi = models.DateTimeField(null=True, blank=True)
    danisma_notu = models.TextField(blank=True)
    danisma_tamamlayan_eczaci = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tamamlanan_danismalar",
    )

    class Meta:
        db_table = "oturum_loglari"
        ordering = ("-olusturulma_tarihi",)
        indexes = [models.Index(fields=["olusturulma_tarihi", "kiosk"])]
        verbose_name = "Oturum Logu"
        verbose_name_plural = "Oturum Loglari"
