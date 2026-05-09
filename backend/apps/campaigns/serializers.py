"""Reklam (kampanya) serileştiricisi.

Legacy: ``ReklamSerializer`` / ``ReklamTakvimSerializer``.
DOOH v2: ``CampaignSerializer`` / ``CreativeSerializer`` / ``ScheduleRuleSerializer``
ve kiosk-edge DTO'lari (``KioskSyncSerializer``, ``KioskPlaylistSerializer``,
``ProofOfPlaySerializer``).
"""
from rest_framework import serializers

from .models import (
    Campaign,
    Creative,
    HouseAd,
    PlayLog,
    Playlist,
    PlaylistItem,
    PricingMatrix,
    Reklam,
    ReklamTakvim,
    ScheduleRule,
)


class ReklamSerializer(serializers.ModelSerializer):
    """
    hedef_eczaneler: M2M Eczane id listesi.
    Yazarken: integer id listesi gonder. Okurken: aynen id listesi doner.
    Bos liste = herkese goster.
    """

    class Meta:
        model = Reklam
        fields = [
            "id",
            "ad",
            "musteri",
            "medya_url",
            "sure_saniye",
            "baslangic_tarihi",
            "bitis_tarihi",
            "yayin_baslangic",
            "yayin_bitis",
            "hedef_eczaneler",
            "aktif",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
            "surum",
        ]
        read_only_fields = ("id", "olusturulma_tarihi", "guncellenme_tarihi", "surum")

    def validate(self, attrs):
        baslangic = attrs.get("baslangic_tarihi", getattr(self.instance, "baslangic_tarihi", None))
        bitis = attrs.get("bitis_tarihi", getattr(self.instance, "bitis_tarihi", None))
        if baslangic and bitis and baslangic >= bitis:
            raise serializers.ValidationError(
                {"bitis_tarihi": "Bitiş tarihi başlangıçtan sonra olmalıdır."}
            )

        sure = attrs.get("sure_saniye", getattr(self.instance, "sure_saniye", None))
        if sure is not None and not 5 <= sure <= 60:
            raise serializers.ValidationError(
                {"sure_saniye": "Yayın süresi 5 ile 60 saniye arasında olmalıdır."}
            )

        return attrs


class ReklamTakvimSerializer(serializers.ModelSerializer):
    reklam_adi = serializers.CharField(source="reklam.ad", read_only=True)
    musteri = serializers.CharField(source="reklam.musteri", read_only=True)
    medya_url = serializers.URLField(source="reklam.medya_url", read_only=True)
    sure_saniye = serializers.IntegerField(source="reklam.sure_saniye", read_only=True)
    kiosk_adi = serializers.CharField(source="kiosk.ad", read_only=True)
    eczane = serializers.IntegerField(source="kiosk.eczane_id", read_only=True)
    eczane_adi = serializers.CharField(source="kiosk.eczane.ad", read_only=True)

    class Meta:
        model = ReklamTakvim
        fields = [
            "id",
            "reklam",
            "reklam_adi",
            "musteri",
            "medya_url",
            "sure_saniye",
            "kiosk",
            "kiosk_adi",
            "eczane",
            "eczane_adi",
            "baslangic_saat",
            "bitis_saat",
            "aktif",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
            "surum",
        ]
        read_only_fields = (
            "id",
            "reklam_adi",
            "musteri",
            "medya_url",
            "sure_saniye",
            "kiosk_adi",
            "eczane",
            "eczane_adi",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
            "surum",
        )

    def validate(self, attrs):
        baslangic = attrs.get("baslangic_saat", getattr(self.instance, "baslangic_saat", None))
        bitis = attrs.get("bitis_saat", getattr(self.instance, "bitis_saat", None))
        if baslangic is None or bitis is None:
            return attrs
        if baslangic < 0 or baslangic > 23 or bitis < 1 or bitis > 24 or baslangic >= bitis:
            raise serializers.ValidationError(
                {"bitis_saat": "Saat aralığı 00-24 içinde olmalı ve bitiş başlangıçtan sonra gelmelidir."}
            )

        reklam = attrs.get("reklam", getattr(self.instance, "reklam", None))
        kiosk = attrs.get("kiosk", getattr(self.instance, "kiosk", None))
        if reklam and kiosk:
            hedefler = reklam.hedef_eczaneler.all()
            if hedefler.exists() and not hedefler.filter(pk=kiosk.eczane_id).exists():
                raise serializers.ValidationError(
                    {"kiosk": "Seçilen kiosk reklamın hedef eczaneleri içinde değil."}
                )

        return attrs


# ─────────────────────────────────────────────────────────────────────────────
# DOOH v2 — Spec-compliant DTOs
# ─────────────────────────────────────────────────────────────────────────────


class CreativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Creative
        fields = ["id", "campaign", "media_url", "duration_seconds", "name", "checksum"]
        read_only_fields = ("id",)

    def validate_duration_seconds(self, value: int) -> int:
        if not 1 <= value <= 60:
            raise serializers.ValidationError("duration_seconds 1..60 arasinda olmalidir.")
        return value


class CampaignSerializer(serializers.ModelSerializer):
    creatives = CreativeSerializer(many=True, read_only=True)

    class Meta:
        model = Campaign
        fields = [
            "id", "advertiser_id", "name", "start_date", "end_date",
            "status", "target_pharmacies", "creatives",
            "olusturulma_tarihi", "guncellenme_tarihi", "surum",
        ]
        read_only_fields = ("id", "creatives", "olusturulma_tarihi",
                            "guncellenme_tarihi", "surum")

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and start >= end:
            raise serializers.ValidationError(
                {"end_date": "end_date, start_date'ten sonra olmalidir."}
            )
        return attrs


class ScheduleRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleRule
        fields = ["id", "campaign", "frequency_type", "frequency_value", "target_hours"]
        read_only_fields = ("id",)

    def validate_target_hours(self, value):
        if value is None:
            return value
        if not isinstance(value, list):
            raise serializers.ValidationError("Liste olmalidir.")
        out = []
        for h in value:
            try:
                ih = int(h)
            except (TypeError, ValueError):
                raise serializers.ValidationError("Her saat 0-23 tamsayisi olmalidir.")
            if not 0 <= ih <= 23:
                raise serializers.ValidationError("Her saat 0-23 araliginda olmalidir.")
            out.append(ih)
        return out


class HouseAdSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseAd
        fields = ["id", "name", "media_url", "duration_seconds", "aktif", "priority"]
        read_only_fields = ("id",)


class PricingMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingMatrix
        fields = [
            "id", "base_price_per_second", "prime_time_coefficient",
            "prime_hours", "frequency_multipliers", "currency", "is_default",
        ]
        read_only_fields = ("id",)


# ── Kiosk Edge DTOs ──

class KioskCreativeSyncSerializer(serializers.ModelSerializer):
    """`/api/kiosk/v1/{kiosk_id}/sync` icindeki tek bir creative."""

    type = serializers.SerializerMethodField()

    class Meta:
        model = Creative
        fields = ["id", "media_url", "duration_seconds", "checksum", "type"]

    def get_type(self, obj):  # noqa: D401
        return "creative"


class KioskHouseAdSyncSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()

    class Meta:
        model = HouseAd
        fields = ["id", "media_url", "duration_seconds", "type"]

    def get_type(self, obj):  # noqa: D401
        return "house_ad"


class KioskPlaylistItemSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    asset_id = serializers.SerializerMethodField()
    asset_type = serializers.SerializerMethodField()

    class Meta:
        model = PlaylistItem
        fields = [
            "id", "asset_id", "asset_type", "media_url",
            "duration_seconds", "playback_order",
            "estimated_start_offset_seconds",
        ]

    def get_media_url(self, obj):
        if obj.creative_id:
            return obj.creative.media_url
        if obj.house_ad_id:
            return obj.house_ad.media_url
        return None

    def get_duration_seconds(self, obj):
        if obj.creative_id:
            return obj.creative.duration_seconds
        if obj.house_ad_id:
            return obj.house_ad.duration_seconds
        return 0

    def get_asset_id(self, obj):
        return str(obj.creative_id or obj.house_ad_id)

    def get_asset_type(self, obj):
        return "creative" if obj.creative_id else "house_ad"


class KioskPlaylistSerializer(serializers.ModelSerializer):
    items = KioskPlaylistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Playlist
        fields = [
            "id", "kiosk", "target_date", "target_hour",
            "loop_duration_seconds", "items",
        ]


class ProofOfPlayItemSerializer(serializers.Serializer):
    """Tek bir PlayLog girdisi (POST body item)."""

    creative_id = serializers.UUIDField(required=False, allow_null=True)
    house_ad_id = serializers.UUIDField(required=False, allow_null=True)
    played_at = serializers.DateTimeField()
    duration_played = serializers.IntegerField(min_value=0, max_value=600)

    def validate(self, attrs):
        if not attrs.get("creative_id") and not attrs.get("house_ad_id"):
            raise serializers.ValidationError(
                "creative_id veya house_ad_id alanlarindan biri zorunludur."
            )
        return attrs


class ProofOfPlayBulkSerializer(serializers.Serializer):
    logs = ProofOfPlayItemSerializer(many=True)


class PlayLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayLog
        fields = ["id", "kiosk", "creative", "house_ad", "played_at", "duration_played"]
        read_only_fields = ("id",)


class PlaylistAdminSerializer(serializers.ModelSerializer):
    """Admin Timeline View icin nested serializer."""

    items = KioskPlaylistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Playlist
        fields = [
            "id", "kiosk", "target_date", "target_hour",
            "loop_duration_seconds", "items",
        ]
