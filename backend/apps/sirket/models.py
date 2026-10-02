from django.db import models

from apps.core.models import BaseModel


class SirketProfili(BaseModel):
    """Platformu işleten tüzel kişiye ait tekil kurumsal profil."""

    sabit_anahtar = models.CharField(max_length=20, unique=True, default="EISA", editable=False)
    ticari_unvan = models.CharField(max_length=255)
    marka_adi = models.CharField(max_length=120, blank=True, default="e-İSA")
    vergi_dairesi = models.CharField(max_length=120)
    vergi_numarasi = models.CharField(max_length=10)
    mersis_numarasi = models.CharField(max_length=16, blank=True, default="")
    ticaret_sicil_numarasi = models.CharField(max_length=50, blank=True, default="")
    kep_adresi = models.EmailField(blank=True, default="")
    eposta = models.EmailField(blank=True, default="")
    telefon = models.CharField(max_length=30, blank=True, default="")
    web_sitesi = models.URLField(blank=True, default="")
    adres = models.TextField()
    ilce = models.CharField(max_length=100, blank=True, default="")
    il = models.CharField(max_length=100, blank=True, default="")
    posta_kodu = models.CharField(max_length=10, blank=True, default="")
    yetkili_ad_soyad = models.CharField(max_length=150, blank=True, default="")
    yetkili_unvan = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        db_table = "sirket_profili"
        verbose_name = "Şirket Profili"
        verbose_name_plural = "Şirket Profili"

    def __str__(self):
        return self.ticari_unvan


class BankaHesabi(BaseModel):
    class ParaBirimi(models.TextChoices):
        TRY = "TRY", "Türk Lirası"
        USD = "USD", "Amerikan Doları"
        EUR = "EUR", "Euro"
        GBP = "GBP", "İngiliz Sterlini"

    sirket = models.ForeignKey(SirketProfili, on_delete=models.CASCADE, related_name="banka_hesaplari")
    banka_adi = models.CharField(max_length=120)
    hesap_sahibi = models.CharField(max_length=255)
    iban = models.CharField(max_length=34)
    sube_adi = models.CharField(max_length=120, blank=True, default="")
    sube_kodu = models.CharField(max_length=20, blank=True, default="")
    hesap_numarasi = models.CharField(max_length=40, blank=True, default="")
    para_birimi = models.CharField(max_length=3, choices=ParaBirimi.choices, default=ParaBirimi.TRY)
    aciklama = models.CharField(max_length=255, blank=True, default="")
    aktif = models.BooleanField(default=True)
    varsayilan = models.BooleanField(default=False)
    sira = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "sirket_banka_hesaplari"
        ordering = ("sira", "banka_adi", "id")
        constraints = [
            models.UniqueConstraint(fields=("sirket", "iban"), name="uniq_sirket_iban"),
            models.UniqueConstraint(
                fields=("sirket",),
                condition=models.Q(varsayilan=True),
                name="uniq_sirket_varsayilan_banka",
            )
        ]
        verbose_name = "Banka Hesabı"
        verbose_name_plural = "Banka Hesapları"

    def __str__(self):
        return f"{self.banka_adi} - {self.iban}"
