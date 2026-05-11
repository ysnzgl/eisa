"""Reklam (kampanya) serileştiricisi — DOOH v2.

``CampaignSerializer`` / ``CreativeSerializer`` / ``ScheduleRuleSerializer``
ve kiosk-edge DTO'lari (``KioskCreativeSyncSerializer``,
``KioskPlaylistSerializer``, ``ProofOfPlay*Serializer``).
"""
from rest_framework import serializers

from .models import (
    Campaign,
    CampaignTarget,
    Creative,
    HouseAd,
    PlayLog,
    Playlist,
    PlaylistItem,
    PricingMatrix,
    ScheduleRule,
)


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


class CampaignTargetSerializer(serializers.ModelSerializer):
    """Kampanya lokasyon hedefi (IL / ILCE / ECZANE)."""

    il_ad = serializers.SerializerMethodField()
    ilce_ad = serializers.SerializerMethodField()
    eczane_ad = serializers.SerializerMethodField()

    class Meta:
        model = CampaignTarget
        fields = ["id", "campaign", "target_type", "il", "ilce", "eczane",
                  "il_ad", "ilce_ad", "eczane_ad"]
        read_only_fields = ("id",)

    def get_il_ad(self, obj):
        return obj.il.ad if obj.il_id else None

    def get_ilce_ad(self, obj):
        return obj.ilce.ad if obj.ilce_id else None

    def get_eczane_ad(self, obj):
        return obj.eczane.ad if obj.eczane_id else None

    def validate(self, attrs):
        tt = attrs.get("target_type")
        if tt == CampaignTarget.TargetType.IL and not attrs.get("il"):
            raise serializers.ValidationError({"il": "IL hedefi için il zorunludur."})
        if tt == CampaignTarget.TargetType.ILCE and not attrs.get("ilce"):
            raise serializers.ValidationError({"ilce": "ILCE hedefi için ilce zorunludur."})
        if tt == CampaignTarget.TargetType.ECZANE and not attrs.get("eczane"):
            raise serializers.ValidationError({"eczane": "ECZANE hedefi için eczane zorunludur."})
        return attrs


class CampaignSerializer(serializers.ModelSerializer):
    creatives = CreativeSerializer(many=True, read_only=True)
    targets = CampaignTargetSerializer(many=True, read_only=True)

    class Meta:
        model = Campaign
        fields = [
            "id", "advertiser_id", "advertiser_name", "name", "start_date", "end_date",
            "status", "target_pharmacies", "targets", "creatives",
            "impression_goal", "frequency_cap_per_hour",
            "olusturulma_tarihi", "guncellenme_tarihi", "surum",
        ]
        read_only_fields = ("id", "creatives", "targets", "olusturulma_tarihi",
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
    campaign_name = serializers.SerializerMethodField()

    class Meta:
        model = PlaylistItem
        fields = [
            "id", "asset_id", "asset_type", "campaign_name", "media_url",
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

    def get_campaign_name(self, obj):
        if obj.creative_id and obj.creative.campaign_id:
            return obj.creative.campaign.name
        if obj.house_ad_id:
            return obj.house_ad.name or "Eczane İçeriği"
        return None


class KioskPlaylistSerializer(serializers.ModelSerializer):
    items = KioskPlaylistItemSerializer(many=True, read_only=True)

    class Meta:
        model = Playlist
        fields = [
            "id", "kiosk", "target_date", "target_hour",
            "loop_duration_seconds", "version", "items",
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
            "loop_duration_seconds", "version", "items",
        ]
