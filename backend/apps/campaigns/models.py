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
    medya_url = models.URLField(max_length=2048, validators=[_https_url_validator])
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


class ReklamTakvim(BaseModel):
    """Reklamin belirli bir kioskta gun ici hangi saatlerde yayinlanacagini tutar."""

    reklam = models.ForeignKey(
        Reklam, on_delete=models.CASCADE, related_name="takvim_atamalari"
    )
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk", on_delete=models.CASCADE, related_name="reklam_takvimi"
    )
    baslangic_saat = models.PositiveSmallIntegerField()
    bitis_saat = models.PositiveSmallIntegerField()
    aktif = models.BooleanField(default=True)

    class Meta:
        db_table = "reklam_takvimi"
        ordering = ("kiosk_id", "baslangic_saat", "bitis_saat")
        verbose_name = "Reklam Takvim Ataması"
        verbose_name_plural = "Reklam Takvim Atamaları"
        constraints = [
            models.CheckConstraint(
                check=models.Q(baslangic_saat__gte=0)
                & models.Q(baslangic_saat__lte=23)
                & models.Q(bitis_saat__gte=1)
                & models.Q(bitis_saat__lte=24)
                & models.Q(baslangic_saat__lt=models.F("bitis_saat")),
                name="reklam_takvimi_saat_araligi_gecerli",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.reklam} -> {self.kiosk} ({self.baslangic_saat}-{self.bitis_saat})"
