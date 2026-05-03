"""Eczane ve kiosk serileştiricileri."""
from rest_framework import serializers

from .models import Eczane, Kiosk


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

    class Meta:
        model = Kiosk
        fields = [
            "id",
            "eczane",
            "eczane_adi",
            "mac_adresi",
            "uygulama_anahtari",
            "aktif",
            "son_goruldu",
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
        )
