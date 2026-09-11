"""Eczane ve kiosk serileştiricileri."""
from rest_framework import serializers

from .models import Eczane, Kiosk, KioskAudioAsset, KioskEczaneAtama, KioskIdleAudio, KioskProvisioningRequest


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


class KioskAudioAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = KioskAudioAsset
        fields = ("id", "original_name", "content_type", "checksum", "aktif", "olusturulma_tarihi")
        read_only_fields = fields


class KioskIdleAudioSerializer(serializers.ModelSerializer):
    asset_id = serializers.IntegerField(source="audio_asset_id", read_only=True)

    class Meta:
        model = KioskIdleAudio
        fields = ("id", "asset_id", "original_name", "content_type", "sira")
        read_only_fields = fields


class KioskSerializer(serializers.ModelSerializer):
    """Kiosk serileştiricisi. uygulama_anahtari salt-okunur (server uretir)."""

    eczane_adi = serializers.CharField(source="eczane.ad", read_only=True)
    il_id      = serializers.IntegerField(source="eczane.il_id", read_only=True)
    il_adi     = serializers.CharField(source="eczane.il.ad", read_only=True)
    ilce_id    = serializers.IntegerField(source="eczane.ilce_id", read_only=True)
    ilce_adi   = serializers.CharField(source="eczane.ilce.ad", read_only=True)
    atama_gecmisi = serializers.SerializerMethodField()
    idle_audio_files = KioskIdleAudioSerializer(many=True, read_only=True)

    def get_atama_gecmisi(self, obj):
        return KioskEczaneAtamaSerializer(
            obj.eczane_atamalari.select_related("eczane", "tasiyan_admin").all(), many=True
        ).data

    def validate(self, attrs):
        if self.instance and "eczane" in attrs and attrs["eczane"].pk != self.instance.eczane_id:
            raise serializers.ValidationError({"eczane": "Eczane değişikliği için Başka Eczaneye Taşı işlemini kullanın."})
        values = {
            "interaction_timeout_seconds": getattr(self.instance, "interaction_timeout_seconds", 20),
            "idle_content_min_seconds": getattr(self.instance, "idle_content_min_seconds", 10),
            "idle_content_max_seconds": getattr(self.instance, "idle_content_max_seconds", 12),
            "idle_content_refresh_seconds": getattr(self.instance, "idle_content_refresh_seconds", 300),
            "idle_audio_delay_seconds": getattr(self.instance, "idle_audio_delay_seconds", 1200),
            "idle_audio_repeat_seconds": getattr(self.instance, "idle_audio_repeat_seconds", 300),
            "idle_audio_schedule_mode": getattr(self.instance, "idle_audio_schedule_mode", "ALL_DAY"),
        }
        values.update({key: attrs[key] for key in values if key in attrs})
        ranges = {
            "interaction_timeout_seconds": (5, 3600),
            "idle_content_min_seconds": (5, 300),
            "idle_content_max_seconds": (5, 300),
            "idle_content_refresh_seconds": (30, 3600),
            "idle_audio_delay_seconds": (60, 86400),
            "idle_audio_repeat_seconds": (60, 86400),
        }
        errors = {}
        for field, (minimum, maximum) in ranges.items():
            if not minimum <= values[field] <= maximum:
                errors[field] = f"Değer {minimum} ile {maximum} saniye arasında olmalıdır."
        if values["idle_content_min_seconds"] > values["idle_content_max_seconds"]:
            errors["idle_content_max_seconds"] = "Maksimum süre minimum süreden küçük olamaz."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

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
            "last_ip",
            "interaction_timeout_seconds",
            "idle_content_min_seconds",
            "idle_content_max_seconds",
            "idle_content_refresh_seconds",
            "idle_audio_delay_seconds",
            "idle_audio_repeat_seconds",
            "idle_audio_schedule_mode",
            "idle_audio_play_on_duty",
            "idle_audio_enabled",
            "idle_audio_media_url",
            "idle_audio_original_name",
            "idle_audio_files",
            # Faz 4/5: DOOH playlist version bilgisi (read-only)
            "last_playlist_version",
            "applied_playlist_version",
            "playlist_applied_at",
            "applied_horizon_start",
            "applied_horizon_end",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
            "surum",
            "atama_gecmisi",
        ]
        read_only_fields = (
            "id",
            "uygulama_anahtari",
            "son_goruldu",
            "last_ip",
            "idle_audio_media_url",
            "idle_audio_original_name",
            "idle_audio_files",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
            "surum",
            "eczane_adi",
            "il_id", "il_adi", "ilce_id", "ilce_adi",
            "last_playlist_version",
            "applied_playlist_version",
            "playlist_applied_at",
            "applied_horizon_start",
            "applied_horizon_end",
            "atama_gecmisi",
        )


class KioskEczaneAtamaSerializer(serializers.ModelSerializer):
    eczane_adi = serializers.CharField(source="eczane.ad", read_only=True)
    tasiyan_admin_adi = serializers.CharField(source="tasiyan_admin.get_full_name", read_only=True, default="")

    class Meta:
        model = KioskEczaneAtama
        fields = ["id", "eczane", "eczane_adi", "baslangic_zamani", "bitis_zamani", "tasima_nedeni", "tasiyan_admin_adi"]
        read_only_fields = fields


class KioskTransferSerializer(serializers.Serializer):
    eczane_id = serializers.IntegerField()
    tasima_nedeni = serializers.CharField(max_length=250, required=False, allow_blank=True, default="")


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

