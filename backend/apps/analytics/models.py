"""Anonim demografik ve davranissal log modelleri (KVKK uyumlu)."""
import uuid

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

    class Meta:
        db_table = "oturum_loglari"
        ordering = ("-olusturulma_tarihi",)
        indexes = [models.Index(fields=["olusturulma_tarihi", "kiosk"])]
        verbose_name = "Oturum Logu"
        verbose_name_plural = "Oturum Loglari"
