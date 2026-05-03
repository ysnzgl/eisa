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
    medya_url = models.URLField(validators=[_https_url_validator])
    baslangic_tarihi = models.DateTimeField()
    bitis_tarihi = models.DateTimeField()

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
