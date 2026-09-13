"""Sadece süper adminler arasında kullanılan iş takip kayıtları."""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Gorev(BaseModel):
    class Durum(models.TextChoices):
        YENI = "YENI", "Yeni"
        INCELENIYOR = "INCELENIYOR", "İnceleniyor"
        YAPILDI = "YAPILDI", "Yapıldı"
        YAPILMADI = "YAPILMADI", "Yapılmadı"

    baslik = models.CharField(max_length=200)
    icerik = models.TextField(max_length=2000)
    durum = models.CharField(max_length=16, choices=Durum.choices, default=Durum.YENI, db_index=True)
    atanan_kullanici = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="atanan_gorevler",
    )

    class Meta:
        db_table = "gorevler"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "İş"
        verbose_name_plural = "İşler"

    def __str__(self) -> str:
        return self.baslik
