"""DOOH reklam (kampanya) modelleri — eczane hedefli."""
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import BaseModel


def _https_url_validator(value: str) -> None:
    """Yalnizca http(s) semalarina izin ver — javascript:/file:/data: bloklanir."""
    lower = (value or "").lower()
    if not (lower.startswith("https://") or lower.startswith("http://")):
        raise ValidationError("medya_url yalnizca http veya https olabilir.")


class Reklam(BaseModel):
    """DOOH idle reklami. Bos hedef_eczaneler = herkese goster."""

    ad = models.CharField(max_length=255)
    musteri = models.CharField(max_length=255, blank=True, default="")
    medya_url = models.URLField(validators=[_https_url_validator])
    sure_saniye = models.PositiveSmallIntegerField(default=15)
    baslangic_tarihi = models.DateTimeField()
    bitis_tarihi = models.DateTimeField()
    yayin_baslangic = models.TimeField(null=True, blank=True, help_text="Günlük yayın başlangıç saati")
    yayin_bitis = models.TimeField(null=True, blank=True, help_text="Günlük yayın bitiş saati")

    hedef_eczaneler = models.ManyToManyField(
        "pharmacies.Eczane", blank=True, related_name="reklamlar"
    )

    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "reklamlar"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Reklam"
        verbose_name_plural = "Reklamlar"

    def __str__(self) -> str:
        return self.ad
