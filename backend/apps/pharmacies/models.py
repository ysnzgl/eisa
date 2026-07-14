"""
Eczane ve Kiosk modelleri.

`Eczane` ve `Kiosk` is-mantigi tablolaridir; `BaseModel`'den turerler
(olusturulma_tarihi, olusturan, guncellenme_tarihi, guncelleyen, surum).

`KioskProvisioningRequest`: Henuz kayitli olmayan kiosk cihazlarinin onay
  bekleyen kayit talepleri. Lifecycle: PENDING → APPROVED/REJECTED.
"""
import uuid

from django.conf import settings
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
    is_online = models.BooleanField(default=False)
    last_playlist_version = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "kiosklar"
        ordering = ("id",)
        verbose_name = "Kiosk"
        verbose_name_plural = "Kiosklar"

    def __str__(self) -> str:
        return self.mac_adresi

    # DRF throttle/permission mekanizmasi request.user.is_authenticated cagirir.
    # Kiosk, Django User degildir; bu property 500'u onler.
    @property
    def is_authenticated(self) -> bool:
        return True


class KioskProvisioningRequest(BaseModel):
    """
    Henuz kayitli olmayan kiosk cihazlarinin onay talepleri.

    Lifecycle: PENDING → APPROVED veya REJECTED.
    Ayni cihaz (MAC) tekrar geldiginde mevcut kayit guncellenir; yeni kayit
    olusturulmaz (idempotent). Onaylandiktan sonra Kiosk FK ile gercek kayda
    baglanir.

    Guvenlik kurallari:
    - Raw fleet_key veya provision_secret SAKLANMAZ.
    - device_metadata icine token, secret, credential YAZILMAZ.
    - Hassas alanlar serializer'da READ-ONLY veya exclude edilir.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Onay Bekliyor"
        APPROVED = "APPROVED", "Onaylandi"
        REJECTED = "REJECTED", "Reddedildi"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Cihaz kimlik bilgileri (istemci tarafindan gonderilir; tek basina guven unsuru sayilmaz)
    mac_adresi = models.CharField(max_length=17, db_index=True)
    hostname = models.CharField(max_length=255, blank=True, default="")
    device_metadata = models.JSONField(
        default=dict, blank=True,
        help_text="Guvenli cihaz/env metadata (token/secret icermez).",
    )

    # Lifecycle
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    last_seen_at = models.DateTimeField(null=True, blank=True, db_index=True)
    request_count = models.PositiveIntegerField(default=1)

    # Onay
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_provisioning_requests",
    )

    # Red
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="rejected_provisioning_requests",
    )
    rejection_reason = models.TextField(blank=True, default="")

    # Onay sonrasi baglanti (SET_NULL: kiosk silinse bile talep korunur)
    kiosk = models.OneToOneField(
        Kiosk,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="provisioning_request",
    )

    class Meta:
        db_table = "kiosk_provisioning_requests"
        ordering = ("-olusturulma_tarihi",)
        verbose_name = "Kiosk Provision Talebi"
        verbose_name_plural = "Kiosk Provision Talepleri"

    def __str__(self) -> str:
        return f"{self.mac_adresi} — {self.status}"
