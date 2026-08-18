"""
Görüş ve Destek modelleri.

DestekParametresi : Tek parametrik tablo — TALEP_TURU, ALAN, ALT_KONU, DURUM grupları.
TalepSayac        : Concurrency-safe yıl bazlı talep no sayacı.
DestekTalebi      : Eczaneden gelen destek talebi (ticket).
DestekYorumu      : Append-only yorum/konuşma geçmişi.
"""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class DestekParametresi(BaseModel):
    """Talep türü, alan, alt konu ve durum için tek parametrik tablo."""

    class Grup(models.TextChoices):
        TALEP_TURU = "TALEP_TURU", "Talep Türü"
        ALAN = "ALAN", "Alan"
        ALT_KONU = "ALT_KONU", "Alt Konu"
        DURUM = "DURUM", "Durum"

    grup = models.CharField(max_length=20, choices=Grup.choices, db_index=True)
    kod = models.CharField(max_length=50, unique=True)
    ad = models.CharField(max_length=100)
    ust_parametre = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="alt_parametreler",
    )
    sira = models.PositiveSmallIntegerField(default=0, db_index=True)
    aktif = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "destek_parametreler"
        ordering = ("grup", "sira", "ad")
        verbose_name = "Destek Parametresi"
        verbose_name_plural = "Destek Parametreleri"

    def __str__(self) -> str:
        return f"{self.grup} / {self.kod} — {self.ad}"


class TalepSayac(models.Model):
    """Concurrency-safe yıl bazlı ticket numara sayacı. BaseModel dışı — audit gerekmez."""

    yil = models.SmallIntegerField(primary_key=True)
    son_sayi = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "destek_talep_sayac"


class DestekTalebi(BaseModel):
    """Eczane kullanıcısının destek talebi."""

    talep_no = models.CharField(max_length=20, unique=True, editable=False, db_index=True)
    eczane = models.ForeignKey(
        "pharmacies.Eczane",
        on_delete=models.PROTECT,
        related_name="destek_talepleri",
    )
    # Ayrı PROTECT FK — ticket sahibi kullanıcı silinse de kayıt korunmalı.
    olusturan_kullanici = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="acilan_destek_talepleri",
    )
    talep_turu = models.ForeignKey(
        DestekParametresi,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Grup: TALEP_TURU",
    )
    alan = models.ForeignKey(
        DestekParametresi,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Grup: ALAN",
    )
    alt_konu = models.ForeignKey(
        DestekParametresi,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Grup: ALT_KONU",
    )
    durum = models.ForeignKey(
        DestekParametresi,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Grup: DURUM",
    )
    kiosk = models.ForeignKey(
        "pharmacies.Kiosk",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="destek_talepleri",
    )
    aciklama = models.TextField(max_length=1000)
    son_hareket_tarihi = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "destek_talepler"
        ordering = ("-son_hareket_tarihi",)
        verbose_name = "Destek Talebi"
        verbose_name_plural = "Destek Talepleri"

    def __str__(self) -> str:
        return self.talep_no


class DestekYorumu(BaseModel):
    """Append-only konuşma geçmişi. olusturan (BaseModel) = yorum yazan kullanıcı."""

    talep = models.ForeignKey(
        DestekTalebi,
        on_delete=models.CASCADE,
        related_name="yorumlar",
    )
    yorum_metni = models.TextField(max_length=1000)

    class Meta:
        db_table = "destek_yorumlar"
        ordering = ("olusturulma_tarihi",)
        verbose_name = "Destek Yorumu"
        verbose_name_plural = "Destek Yorumları"

    def __str__(self) -> str:
        return f"{self.talep_id} yorumu"
