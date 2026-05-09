"""
Sikayet kategorileri, sorular, cevaplar ve etken madde onerileri.

Marka onerisi YASAKTIR — yalnizca jenerik etken maddeler.
"""
from django.db import models

from apps.core.models import BaseModel


class Kategori(BaseModel):
    """Sikayet kategorisi (Uyku, Enerji, Bagisiklik vb.) veya 'Hassas Durum'."""

    ad = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(unique=True)
    ikon = models.CharField(max_length=64, default="fa-circle")
    hassas = models.BooleanField(
        default=False,
        help_text="Sessiz triyaj akisi (Akis B) icin isaretle.",
    )
    aktif = models.BooleanField(default=True)

    hedef_cinsiyet = models.ForeignKey(
        "lookups.Cinsiyet", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="hedef_kategoriler",
        help_text="Bos = tum cinsiyetlere goster.",
    )
    hedef_yas_araliklari = models.ManyToManyField(
        "lookups.YasAraligi", blank=True, related_name="hedef_kategoriler",
        help_text="Bos = herkese goster.",
    )

    class Meta:
        db_table = "kategoriler"
        ordering = ("ad",)
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"

    def __str__(self) -> str:
        return self.ad


class Soru(BaseModel):
    kategori = models.ForeignKey(
        Kategori, on_delete=models.CASCADE, related_name="sorular"
    )
    metin = models.TextField()
    sira = models.PositiveSmallIntegerField(default=1)

    hedef_cinsiyet = models.ForeignKey(
        "lookups.Cinsiyet", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="hedef_sorular",
        help_text="Bos = tum cinsiyetlere goster.",
    )
    hedef_yas_araliklari = models.ManyToManyField(
        "lookups.YasAraligi", blank=True, related_name="hedef_sorular",
        help_text="Bos = herkese goster.",
    )
    hedef_etken_maddeler = models.ManyToManyField(
        "EtkenMadde", blank=True, through="SoruEtkenMadde",
        related_name="hedef_sorular",
        help_text="Bos = herkese goster.",
    )

    class Meta:
        db_table = "sorular"
        ordering = ("kategori__ad", "sira")
        unique_together = [("kategori", "sira")]
        verbose_name = "Soru"
        verbose_name_plural = "Sorular"

    def __str__(self) -> str:  # pragma: no cover
        return self.metin[:64]


class Cevap(BaseModel):
    soru = models.ForeignKey(Soru, on_delete=models.CASCADE, related_name="cevaplar")
    metin = models.CharField(max_length=255)
    agirlik = models.IntegerField(default=0)

    class Meta:
        db_table = "cevaplar"
        ordering = ("soru_id", "-agirlik")
        verbose_name = "Cevap"
        verbose_name_plural = "Cevaplar"

    def __str__(self) -> str:  # pragma: no cover
        return self.metin


class EtkenMadde(BaseModel):
    """Etken madde (Magnezyum, B12 vb.). Marka onerisi YASAKTIR."""

    ad = models.CharField(max_length=250, unique=True)
    aciklama = models.TextField(blank=True, default="")
    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "etken_maddeler"
        ordering = ("ad",)
        verbose_name = "Etken Madde"
        verbose_name_plural = "Etken Maddeler"

    def __str__(self) -> str:
        return self.ad


class SoruEtkenMadde(models.Model):
    """Soru ile EtkenMadde arasındaki ilişki — rol bilgisi içerir.

    unique_together garantisi: aynı soruya aynı etken madde bir kez eklenebilir.
    """

    ROL_ANA = "ana"
    ROL_DESTEKLEYICI = "destekleyici"
    ROL_SECENEKLER = [
        (ROL_ANA, "Ana"),
        (ROL_DESTEKLEYICI, "Destekleyici"),
    ]

    soru = models.ForeignKey(
        Soru, on_delete=models.CASCADE, related_name="etken_madde_baglantilari"
    )
    etken_madde = models.ForeignKey(
        EtkenMadde, on_delete=models.CASCADE, related_name="soru_baglantilari"
    )
    rol = models.CharField(max_length=16, choices=ROL_SECENEKLER, default=ROL_ANA)

    class Meta:
        db_table = "soru_etken_maddeler"
        unique_together = (("soru", "etken_madde"),)
        verbose_name = "Soru Etken Madde"
        verbose_name_plural = "Soru Etken Maddeler"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.soru_id} — {self.etken_madde.ad} ({self.rol})"
