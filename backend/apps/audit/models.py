"""
Hafif is-mantigi denetim (audit) loglari.

Sadece kritik olaylar yazilir:
  - Super Admin CRUD islemleri
  - Kiosk online/offline ve heartbeat olaylari
Sistem/exception loglari buraya YAZILMAZ; dosya tabanli JSON loglara gider.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class DenetimLogu(models.Model):
    """Denetlenebilir is-mantigi olaylari. Append-only — BaseModel'den TUREMEZ."""

    class Eylem(models.TextChoices):
        OLUSTUR = "create", "Olustur"
        GUNCELLE = "update", "Guncelle"
        SIL = "delete", "Sil"
        GIRIS = "login", "Giris"
        GIRIS_BASARISIZ = "login_failed", "Giris Basarisiz"
        KIOSK_ONLINE = "kiosk_online", "Kiosk Online"
        KIOSK_OFFLINE = "kiosk_offline", "Kiosk Offline"
        KIOSK_HEARTBEAT = "kiosk_heartbeat", "Kiosk Heartbeat"
        ANAHTAR_YENILE = "regenerate_key", "App-Key Yenile"
        DIGER = "other", "Diger"

    aktor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="denetim_loglari",
        help_text="Islemi yapan kullanici. Kiosk olaylari icin NULL olabilir.",
    )
    aktor_ozeti = models.CharField(max_length=255, blank=True, default="")
    eylem = models.CharField(max_length=32, choices=Eylem.choices)
    hedef_tipi = models.CharField(max_length=64, blank=True, default="")
    hedef_id = models.CharField(max_length=64, blank=True, default="")
    ozet = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    kiosk_mac = models.CharField(max_length=17, blank=True, default="")
    ip_adresi = models.GenericIPAddressField(null=True, blank=True)

    olusturulma_tarihi = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "denetim_loglari"
        ordering = ("-olusturulma_tarihi",)
        indexes = [
            models.Index(fields=["eylem", "olusturulma_tarihi"]),
            models.Index(fields=["hedef_tipi", "hedef_id"]),
            models.Index(fields=["kiosk_mac", "olusturulma_tarihi"]),
        ]
        verbose_name = "Denetim Logu"
        verbose_name_plural = "Denetim Loglari"

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.olusturulma_tarihi:%Y-%m-%d %H:%M}] {self.aktor_ozeti or '-'} {self.eylem} {self.hedef_tipi}#{self.hedef_id}"


def kayit_birak(
    *,
    eylem: str,
    aktor=None,
    hedef=None,
    hedef_tipi: str = "",
    hedef_id: str = "",
    ozet: str = "",
    metadata: dict | None = None,
    kiosk_mac: str = "",
    ip_adresi: str | None = None,
) -> DenetimLogu:
    """Tek satirda denetim kaydi yaratan yardimci."""
    if hedef is not None and not hedef_tipi:
        hedef_tipi = hedef.__class__.__name__
        hedef_id = str(getattr(hedef, "pk", "") or "")

    return DenetimLogu.objects.create(
        aktor=aktor if getattr(aktor, "pk", None) else None,
        aktor_ozeti=str(aktor) if aktor is not None else "",
        eylem=eylem,
        hedef_tipi=hedef_tipi or "",
        hedef_id=str(hedef_id or ""),
        ozet=ozet[:255],
        metadata=metadata or {},
        kiosk_mac=kiosk_mac or "",
        ip_adresi=ip_adresi,
    )
