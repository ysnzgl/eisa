"""
Eczane ve Kiosk modelleri.

`Eczane` ve `Kiosk` is-mantigi tablolaridir; `BaseModel`'den turerler
(olusturulma_tarihi, olusturan, guncellenme_tarihi, guncelleyen, surum).
"""
from django.db import models

from apps.core.models import BaseModel


class Eczane(BaseModel):
    """Eczane (kiosk barindiran fiziksel lokasyon)."""

    ad = models.CharField(max_length=255)
    il = models.ForeignKey(
        "lookups.Il", on_delete=models.PROTECT, related_name="eczaneler"
    )
    ilce = models.ForeignKey(
        "lookups.Ilce", on_delete=models.PROTECT, related_name="eczaneler"
    )
    adres = models.TextField(blank=True, default="")
    sahip_adi = models.CharField(max_length=128, blank=True, default="")
    telefon = models.CharField(max_length=20, blank=True, default="")
    eczane_kodu = models.CharField(
        max_length=32, unique=True, null=True, blank=True,
        help_text="Elle girilen eczane kodu (opsiyonel).",
    )
    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "eczaneler"
        ordering = ("ad",)
        verbose_name = "Eczane"
        verbose_name_plural = "Eczaneler"

    def __str__(self) -> str:
        return self.ad


class Kiosk(BaseModel):
    """Eczanedeki fiziksel kiosk cihaz. App-Key + MAC eslesmesi ile yetkilenir."""

    eczane = models.ForeignKey(
        Eczane, on_delete=models.CASCADE, related_name="kiosklar"
    )
    ad = models.CharField(max_length=50, unique=False, blank=False, null=False)
    mac_adresi = models.CharField(max_length=17, unique=True)
    uygulama_anahtari = models.CharField(max_length=128, unique=True)
    aktif = models.BooleanField(default=True)
    son_goruldu = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "kiosklar"
        ordering = ("id",)
        verbose_name = "Kiosk"
        verbose_name_plural = "Kiosklar"

    def __str__(self) -> str:
        return self.mac_adresi
