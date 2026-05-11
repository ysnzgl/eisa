"""
Lookup (Sabit) Tablolari.

Veri tekrarini onlemek icin tum metin-bazli sabit degerler ayri tablolarda
tutulur ve diger modellerde Foreign Key olarak referans edilir.

Onemli: Bu modeller `BaseModel`'den TUREMEZ — surum/audit kolonlari TASIMAZ.
Referans verisidir; degismez/nadir guncellenir.
"""
from __future__ import annotations

from django.db import models

from apps.core.models import LookupModel


class Il(LookupModel):
    """Sehirler (Iller) — Eczane.il referansi."""

    ad = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = "iller"
        ordering = ("ad",)
        verbose_name = "Il"
        verbose_name_plural = "Iller"

    def __str__(self) -> str:
        return self.ad


class Ilce(LookupModel):
    """Ilceler — Eczane.ilce referansi."""

    il = models.ForeignKey(Il, on_delete=models.PROTECT, related_name="ilceler")
    ad = models.CharField(max_length=64)

    class Meta:
        db_table = "ilceler"
        ordering = ("il__ad", "ad")
        unique_together = (("il", "ad"),)
        verbose_name = "Ilce"
        verbose_name_plural = "Ilceler"

    def __str__(self) -> str:
        return f"{self.ad} / {self.il.ad}"


class Cinsiyet(LookupModel):
    """Cinsiyet sabitleri (Kadin, Erkek, Diger)."""

    kod = models.CharField(max_length=4, unique=True)  # F, M, O
    ad = models.CharField(max_length=32, unique=True)

    class Meta:
        db_table = "cinsiyetler"
        ordering = ("ad",)
        verbose_name = "Cinsiyet"
        verbose_name_plural = "Cinsiyetler"

    def __str__(self) -> str:
        return self.ad


class YasAraligi(LookupModel):
    """Yas araliklari (0-17, 18-25, 26-35, 36-50, 51-65, 65+)."""

    kod = models.CharField(max_length=8, unique=True)   # "18-25"
    ad = models.CharField(max_length=32)
    alt_sinir = models.PositiveSmallIntegerField()
    ust_sinir = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = "yas_araliklari"
        ordering = ("alt_sinir",)
        verbose_name = "Yas Araligi"
        verbose_name_plural = "Yas Araliklari"

    def __str__(self) -> str:
        return self.ad
