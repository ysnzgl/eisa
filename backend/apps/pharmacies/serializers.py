"""Eczane ve kiosk serileştiricileri."""
from rest_framework import serializers

from .models import Eczane, Kiosk, KioskProvisioningRequest


class EczaneSerializer(serializers.ModelSerializer):
    """Eczane CRUD serileştiricisi. Lookup id'lerini direkt alir; isimleri read-only doner."""

    il_adi = serializers.CharField(source="il.ad", read_only=True)
    ilce_adi = serializers.CharField(source="ilce.ad", read_only=True)
    kiosk_sayisi = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Eczane
        fields = [
            "id",
            "ad",
            "il",
            "il_adi",
            "ilce",
            "ilce_adi",
            "adres",
            "sahip_adi",
            "telefon",
            "eczane_kodu",
            "aktif",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
            "surum",
            "kiosk_sayisi",
        ]
        read_only_fields = (
            "id",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
            "surum",
            "kiosk_sayisi",
            "il_adi",
            "ilce_adi",
        )


class KioskSerializer(serializers.ModelSerializer):
    """Kiosk serileştiricisi. uygulama_anahtari salt-okunur (server uretir)."""

    eczane_adi = serializers.CharField(source="eczane.ad", read_only=True)
    il_id      = serializers.IntegerField(source="eczane.il_id", read_only=True)
    il_adi     = serializers.CharField(source="eczane.il.ad", read_only=True)
    ilce_id    = serializers.IntegerField(source="eczane.ilce_id", read_only=True)
    ilce_adi   = serializers.CharField(source="eczane.ilce.ad", read_only=True)

    class Meta:
        model = Kiosk
        fields = [
            "id",
            "eczane",
            "eczane_adi",
            "il_id",
            "il_adi",
            "ilce_id",
            "ilce_adi",
            "ad",
            "mac_adresi",
            "uygulama_anahtari",
            "aktif",
            "son_goruldu",
            "is_online",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
            "surum",
        ]
        read_only_fields = (
            "id",
            "uygulama_anahtari",
            "son_goruldu",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
            "surum",
            "eczane_adi",
            "il_id", "il_adi", "ilce_id", "ilce_adi",
        )


# ── KioskProvisioningRequest Serializer'ları ─────────────────────────────────

class KioskProvisioningRequestSerializer(serializers.ModelSerializer):
    """
    Onay bekleyen cihaz listesi/detay serileştiricisi (SuperAdmin).

    Güvenlik: fleet_key, provision_secret, token veya ham credential
    alanları bu serializer'a EKLENMEZ.
    """

    approved_by_username = serializers.CharField(
        source="approved_by.username", read_only=True, default=None
    )
    rejected_by_username = serializers.CharField(
        source="rejected_by.username", read_only=True, default=None
    )
    first_seen_at = serializers.DateTimeField(source="olusturulma_tarihi", read_only=True)
    kiosk_id = serializers.IntegerField(source="kiosk.id", read_only=True, default=None)
    kiosk_ad = serializers.CharField(source="kiosk.ad", read_only=True, default=None)

    class Meta:
        model = KioskProvisioningRequest
        fields = [
            "id",
            "mac_adresi",
            "hostname",
            "device_metadata",
            "status",
            "first_seen_at",
            "last_seen_at",
            "request_count",
            "approved_at",
            "approved_by_username",
            "rejected_at",
            "rejected_by_username",
            "rejection_reason",
            "kiosk_id",
            "kiosk_ad",
        ]
        read_only_fields = fields


class KioskProvisioningApproveSerializer(serializers.Serializer):
    """Cihaz onaylama isteği — eczane ve kiosk adı zorunlu."""

    eczane_id = serializers.IntegerField()
    ad = serializers.CharField(max_length=50)


class KioskProvisioningRejectSerializer(serializers.Serializer):
    """Cihaz reddetme isteği — red nedeni opsiyonel."""

    rejection_reason = serializers.CharField(max_length=500, allow_blank=True, default="")

