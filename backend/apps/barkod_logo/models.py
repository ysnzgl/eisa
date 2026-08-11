"""Barkod Logo modeli — QR/barkod fiş baskısında e-ISA başlık alanı için logo rotasyon sistemi.

DOOH kampanya sisteminden tamamen bağımsızdır. Fişteki sabit 'e-ISA' başlığının
yerini alır; QR kodunu veya fiş içeriğini değiştirmez.
"""
import uuid

from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import BaseModel


class BarkodLogo(BaseModel):
    """Kiosk fiş baskısında kullanılacak logo kaydı."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad = models.CharField(max_length=255)

    # Depolama alanı referansları (StorageService ile upload edilen PNG)
    media_url = models.CharField(
        max_length=2048,
        blank=True,
        default="",
        help_text="Görselin kalıcı public URL'si.",
    )
    object_key = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        help_text="RustFS/S3 nesne anahtarı.",
    )
    checksum = models.CharField(
        max_length=80,
        blank=True,
        default="",
        help_text="sha256:<hex> formatında dosya özeti.",
    )

    # Yayın penceresi (UTC olarak saklanır; Istanbul takvimi katalog endpoint'inde hesaplanır)
    baslangic_zamani = models.DateTimeField(
        help_text="Logo rotasyonunun başlayacağı UTC zaman.",
    )
    bitis_zamani = models.DateTimeField(
        help_text="Logo rotasyonunun sona ereceği UTC zaman (bu an dahil DEĞİL).",
    )

    aktif = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Pasif logolar bir sonraki başarılı katalog senkronizasyonundan sonra rotasyondan çıkar.",
    )

    # Kiosk başına günlük baskı limiti — null = sınırsız
    gunluk_baski_limiti = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text=(
            "Her bir kioskta, bir takvim günü içinde yapılabilecek en fazla baskı sayısıdır. "
            "Boş bırakılırsa sınırsızdır."
        ),
    )

    # Hedef kiosk ilişkisi — boş bırakılırsa hiçbir kioska gönderilmez
    hedef_kiosklar = models.ManyToManyField(
        "pharmacies.Kiosk",
        blank=True,
        related_name="barkod_logolar",
        help_text="Bu logoyu alacak kiosklar. Boş bırakılırsa hiçbir kioska dağıtılmaz.",
    )

    class Meta:
        db_table = "barkod_logolar"
        ordering = ("olusturulma_tarihi", "id")
        verbose_name = "Barkod Logo"
        verbose_name_plural = "Barkod Logolar"

    def __str__(self) -> str:
        return self.ad
