"""Reklam (kampanya) serileştiricisi — DOOH v2.

``CampaignSerializer`` / ``CreativeSerializer`` / ``ScheduleRuleSerializer``
ve kiosk-edge DTO'lari (``KioskCreativeSyncSerializer``,
``KioskPlaylistSerializer``, ``ProofOfPlay*Serializer``).
"""
from django.conf import settings
from rest_framework import serializers

from .models import (
    Campaign,
    CampaignTarget,
    CampaignTotalAllocation,
    Creative,
    DayPlan,
    DeliveryRule,
    GenerationJob,
    HouseAd,
    HourPlan,
    KioskDayQuota,
    KioskDesiredBundle,
    PlanningRun,
    PlayLog,
    Playlist,
    PlaylistItem,
    PlaylistTemplate,
    PricingMatrix,
    ScheduleRule,
)


# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı — kalıcı URL'den object_key türetme
# ─────────────────────────────────────────────────────────────────────────────


def _derive_object_key_from_url(media_url: str) -> str:
    """media_url bilinen S3_PUBLIC_BASE_URL ile başlıyorsa object_key'i döndürür.

    Sözleşme: S3_PUBLIC_BASE_URL bucket adını içerir.
      Örn: S3_PUBLIC_BASE_URL=https://files.eisa.com.tr/eisa-files
           media_url=https://files.eisa.com.tr/eisa-files/ads/abc.mp4
           → object_key=ads/abc.mp4

    Presigned URL (X-Amz-*), yabancı host veya eksik S3_PUBLIC_BASE_URL → boş döner.
    Backfill için: python manage.py backfill_media_object_keys
    """
    if not media_url:
        return ""
    # Presigned URL → türetme denenmez
    if "X-Amz-" in media_url or "x-amz-" in media_url:
        return ""
    base = getattr(settings, "S3_PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        return ""
    expected_prefix = f"{base}/"
    if media_url.startswith(expected_prefix):
        key = media_url[len(expected_prefix):]
        # Path traversal koruması
        if ".." in key or "//" in key:
            return ""
        return key
    return ""


# DOOH v2 — Spec-compliant DTOs
# ─────────────────────────────────────────────────────────────────────────────


class CreativeSerializer(serializers.ModelSerializer):
    is_grid_compliant = serializers.BooleanField(read_only=True)

    _GRID_DURATIONS = frozenset({15, 30, 45, 60})

    class Meta:
        model = Creative
        fields = ["id", "campaign", "media_url", "duration_seconds", "name",
                  "checksum", "object_key", "weight", "is_grid_compliant"]
        read_only_fields = ("id", "is_grid_compliant")

    def validate_duration_seconds(self, value: int) -> int:
        if not 1 <= value <= 60:
            raise serializers.ValidationError("duration_seconds 1..60 arasinda olmalidir.")
        # Grid validasyonu: yeni kayit veya deger degisiyorsa {15,30,45,60} zorunlu.
        # Legacy kayit ayni degerle kaydediliyorsa izin verilir.
        instance = getattr(self, "instance", None)
        if instance and int(instance.duration_seconds) == int(value):
            return value  # Legacy deger degismeden korunuyor
        if value not in self._GRID_DURATIONS:
            raise serializers.ValidationError(
                f"duration_seconds {value} 15sn grid ile uyumsuz. "
                f"Izin verilen: 15 / 30 / 45 / 60 saniye."
            )
        return value

    def validate(self, attrs):
        if not attrs.get("object_key"):
            attrs["object_key"] = _derive_object_key_from_url(attrs.get("media_url", ""))
        return attrs


class CampaignTargetSerializer(serializers.ModelSerializer):
    """Kampanya lokasyon hedefi (IL / ILCE / ECZANE / KIOSK)."""

    il_ad = serializers.SerializerMethodField()
    ilce_ad = serializers.SerializerMethodField()
    eczane_ad = serializers.SerializerMethodField()
    kiosk_ad = serializers.SerializerMethodField()

    class Meta:
        model = CampaignTarget
        fields = ["id", "campaign", "target_type", "mode",
                  "il", "ilce", "eczane", "kiosk",
                  "il_ad", "ilce_ad", "eczane_ad", "kiosk_ad"]
        read_only_fields = ("id",)

    def get_il_ad(self, obj):
        return obj.il.ad if obj.il_id else None

    def get_ilce_ad(self, obj):
        return obj.ilce.ad if obj.ilce_id else None

    def get_eczane_ad(self, obj):
        return obj.eczane.ad if obj.eczane_id else None

    def get_kiosk_ad(self, obj):
        return str(obj.kiosk.mac_adresi) if obj.kiosk_id else None

    def validate(self, attrs):
        tt = attrs.get("target_type")
        if tt == CampaignTarget.TargetType.IL and not attrs.get("il"):
            raise serializers.ValidationError({"il": "IL hedefi icin il zorunludur."})
        if tt == CampaignTarget.TargetType.ILCE and not attrs.get("ilce"):
            raise serializers.ValidationError({"ilce": "ILCE hedefi icin ilce zorunludur."})
        if tt == CampaignTarget.TargetType.ECZANE and not attrs.get("eczane"):
            raise serializers.ValidationError({"eczane": "ECZANE hedefi icin eczane zorunludur."})
        if tt == CampaignTarget.TargetType.KIOSK and not attrs.get("kiosk"):
            raise serializers.ValidationError({"kiosk": "KIOSK hedefi icin kiosk zorunludur."})
        return attrs


class CampaignSerializer(serializers.ModelSerializer):
    creatives = CreativeSerializer(many=True, read_only=True)
    targets = CampaignTargetSerializer(many=True, read_only=True)
    effective_state = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id", "advertiser_id", "advertiser_name", "name", "start_date", "end_date",
            "status", "effective_state", "target_scope", "follows",
            "targets", "creatives",
            "priority",
            "olusturulma_tarihi", "guncellenme_tarihi", "surum",
        ]
        read_only_fields = (
            "id", "effective_state", "creatives", "targets",
            "olusturulma_tarihi", "guncellenme_tarihi", "surum",
            "follows",        # yalniz set_campaign_follows() servisi uzerinden
        )

    def get_effective_state(self, obj):
        return obj.effective_state

    def validate(self, attrs):
        is_create = self.instance is None

        # 1. target_scope yeni kayıtta zorunlu
        if is_create and not attrs.get("target_scope"):
            raise serializers.ValidationError(
                {"target_scope": (
                    "target_scope yeni kampanya oluştururken zorunludur. "
                    "Değerler: ALL (tum aktif kiosklar) | RULES (CampaignTarget kuralları)."
                )}
            )

        # 2. Faz 7: Deprecated alanlar kaldırıldı — herhangi değer gönderilirse 400 ver.
        # Bu alanlar Campaign modelinden silindi (migration 0020); sessizce ignore edilmez.
        if self.initial_data:
            _DEPRECATED_FIELDS = {
                "is_guaranteed": "is_guaranteed Faz 7'de kaldirildi. DeliveryRule.guarantee_mode kullanin.",
                "impression_goal": "impression_goal Faz 7'de kaldirildi. DeliveryRule(CAMPAIGN_TOTAL) kullanin.",
                "frequency_cap_per_hour": "frequency_cap_per_hour Faz 7'de kaldirildi. DeliveryRule.max_per_hour kullanin.",
            }
            errors = {}
            for field, msg in _DEPRECATED_FIELDS.items():
                if field in self.initial_data:
                    errors[field] = msg
            if errors:
                raise serializers.ValidationError(errors)

        # 3. start/end tarih tutarlilik
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
    is_grid_compliant = serializers.BooleanField(read_only=True)

    _GRID_DURATIONS = frozenset({15, 30, 45, 60})

    class Meta:
        model = HouseAd
        fields = ["id", "name", "media_url", "duration_seconds", "aktif",
                  "priority", "object_key", "is_grid_compliant"]
        read_only_fields = ("id", "is_grid_compliant")

    def validate_duration_seconds(self, value: int) -> int:
        if not 1 <= value <= 60:
            raise serializers.ValidationError("duration_seconds 1..60 arasinda olmalidir.")
        instance = getattr(self, "instance", None)
        if instance and int(instance.duration_seconds) == int(value):
            return value  # Legacy deger degismeden korunuyor
        if value not in self._GRID_DURATIONS:
            raise serializers.ValidationError(
                f"duration_seconds {value} 15sn grid ile uyumsuz. "
                f"Izin verilen: 15 / 30 / 45 / 60 saniye."
            )
        return value

    def validate(self, attrs):
        if not attrs.get("object_key"):
            attrs["object_key"] = _derive_object_key_from_url(attrs.get("media_url", ""))
        return attrs


class PricingMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingMatrix
        fields = [
            "id", "base_price_per_second", "prime_time_coefficient",
            "prime_hours", "frequency_multipliers", "currency", "is_default",
        ]
        read_only_fields = ("id",)


class DeliveryRuleSerializer(serializers.ModelSerializer):
    """Faz 1: Campaign icin yayın frekans + garanti kuralı (ScheduleRule'un halefi)."""

    class Meta:
        model = DeliveryRule
        fields = [
            "id", "campaign", "delivery_type", "count",
            "window_start_time", "window_end_time",
            "active_hours", "active_weekdays",
            "guarantee_mode", "max_per_hour",
        ]
        read_only_fields = ("id",)

    def validate_active_hours(self, value):
        if value is None:
            return value
        if not isinstance(value, list):
            raise serializers.ValidationError("Liste olmalidir.")
        for h in value:
            try:
                ih = int(h)
            except (TypeError, ValueError):
                raise serializers.ValidationError("Her saat 0-23 tamsayisi olmalidir.")
            if not 0 <= ih <= 23:
                raise serializers.ValidationError("Her saat 0-23 araliginda olmalidir.")
        return value

    def validate(self, attrs):
        delivery_type = attrs.get("delivery_type")
        if delivery_type == DeliveryRule.DeliveryType.LEGACY_PER_LOOP:
            raise serializers.ValidationError(
                "LEGACY_PER_LOOP API uzerinden yazilamaz. "
                "Bu tip yalniz legacy ScheduleRule donusumunde salt-okunur olarak korunur."
            )
        if delivery_type == DeliveryRule.DeliveryType.TIME_WINDOW:
            if not attrs.get("window_start_time") or not attrs.get("window_end_time"):
                raise serializers.ValidationError(
                    "TIME_WINDOW icin window_start_time ve window_end_time zorunludur."
                )
        return attrs


# ── Kiosk Edge DTOs ──

class KioskCreativeSyncSerializer(serializers.ModelSerializer):
    """`/api/kiosk/v1/sync` icindeki tek bir creative."""

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


# ── GenerationJob + PlaylistTemplate ─────────────────────────────────────────

class GenerationJobSerializer(serializers.ModelSerializer):
    progress_pct = serializers.IntegerField(read_only=True)
    # Backward-compat alias: eski API 'job_id' bekliyordu; yeni clients 'id' kullanır
    job_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = GenerationJob
        fields = [
            "id", "job_id",  # job_id = backward-compat alias for id
            "target_date", "kiosk", "status", "triggered_by",
            "total_kiosks", "done_kiosks", "failed_kiosks", "playlists_generated",
            "progress_pct", "error_detail", "started_at", "finished_at",
            "olusturulma_tarihi",
            # Faz 4 queue fields (read-only summary)
            "attempt_count", "max_attempts", "available_at", "dedupe_key", "payload",
        ]
        read_only_fields = fields


class PlaylistTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaylistTemplate
        fields = [
            "id", "name", "loop_duration_seconds", "slots", "target_hours",
            "description", "olusturulma_tarihi", "guncellenme_tarihi",
        ]
        read_only_fields = ("id", "olusturulma_tarihi", "guncellenme_tarihi")

    def validate_slots(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("slots bir liste olmalidir.")
        required = {"duration_seconds"}
        for i, slot in enumerate(value):
            missing = required - set(slot.keys())
            if missing:
                raise serializers.ValidationError(
                    f"slots[{i}]: eksik alan(lar) {missing}"
                )
            if not 1 <= int(slot["duration_seconds"]) <= 60:
                raise serializers.ValidationError(
                    f"slots[{i}].duration_seconds 1..60 arasinda olmalidir."
                )
        return value


# ── HourPlan + DayPlan ────────────────────────────────────────────────────────

class HourPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = HourPlan
        fields = [
            "id", "name", "description", "slots",
            "olusturulma_tarihi", "guncellenme_tarihi",
        ]
        read_only_fields = ("id", "olusturulma_tarihi", "guncellenme_tarihi")

    def validate_slots(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("slots bir liste olmalidir.")
        total_minutes = 0
        for i, slot in enumerate(value):
            for required_field in ("offset_minutes", "duration_minutes", "loop_template_id"):
                if required_field not in slot:
                    raise serializers.ValidationError(
                        f"slots[{i}]: '{required_field}' alani eksik."
                    )
            offset = int(slot["offset_minutes"])
            duration = int(slot["duration_minutes"])
            if not 0 <= offset <= 59:
                raise serializers.ValidationError(
                    f"slots[{i}].offset_minutes 0..59 arasinda olmalidir."
                )
            if duration < 1:
                raise serializers.ValidationError(
                    f"slots[{i}].duration_minutes en az 1 olmalidir."
                )
            total_minutes += duration
        if total_minutes > 60:
            raise serializers.ValidationError(
                f"Toplam duration_minutes ({total_minutes}) 60 dakikayi gecemez."
            )
        return value


class DayPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = DayPlan
        fields = [
            "id", "name", "description", "slots",
            "olusturulma_tarihi", "guncellenme_tarihi",
        ]
        read_only_fields = ("id", "olusturulma_tarihi", "guncellenme_tarihi")

    def validate_slots(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("slots bir liste olmalidir.")
        seen_hours = set()
        for i, slot in enumerate(value):
            for required_field in ("hour", "hour_plan_id"):
                if required_field not in slot:
                    raise serializers.ValidationError(
                        f"slots[{i}]: '{required_field}' alani eksik."
                    )
            hour = int(slot["hour"])
            if not 0 <= hour <= 23:
                raise serializers.ValidationError(
                    f"slots[{i}].hour 0..23 arasinda olmalidir."
                )
            if hour in seen_hours:
                raise serializers.ValidationError(
                    f"Saat {hour} birden fazla kez tanimlanmis."
                )
            seen_hours.add(hour)
        return value


# ─────────────────────────────────────────────────────────────────────────────
# Faz 3 — Simulation + Activation response serializers
# ─────────────────────────────────────────────────────────────────────────────


class KioskDaySimResultSerializer(serializers.Serializer):
    """Tek kiosk+tarih simülasyon sonucu."""

    kiosk_id = serializers.IntegerField()
    date = serializers.DateField()
    requested = serializers.IntegerField()
    placed = serializers.IntegerField()
    unplaced = serializers.IntegerField()
    capacity_used_seconds = serializers.IntegerField()
    blocking_reasons = serializers.ListField(child=serializers.CharField(), default=list)
    fingerprint = serializers.CharField(default="")


class SimulationResultSerializer(serializers.Serializer):
    """Campaign simülasyon API yanıtı (POST /simulate/)."""

    campaign_id = serializers.UUIDField()
    fingerprint = serializers.CharField()
    target_kiosks = serializers.ListField(child=serializers.IntegerField())
    date_range = serializers.ListField(child=serializers.DateField())
    kiosk_days = KioskDaySimResultSerializer(many=True)
    total_requested = serializers.IntegerField()
    total_placed = serializers.IntegerField()
    total_unplaced = serializers.IntegerField()
    would_succeed = serializers.BooleanField()
    blocking_reasons = serializers.ListField(child=serializers.CharField(), default=list)


class ActivationResultSerializer(serializers.Serializer):
    """Campaign aktivasyon API yanıtı (POST /activate/)."""

    campaign_id = serializers.UUIDField()
    planning_run_id = serializers.UUIDField(allow_null=True)
    activated_kiosks = serializers.IntegerField()
    activated_dates = serializers.IntegerField()
    total_placements = serializers.IntegerField()
    fingerprint = serializers.CharField()
    is_complete = serializers.BooleanField()
    blocking_reasons = serializers.ListField(child=serializers.CharField(), default=list)
