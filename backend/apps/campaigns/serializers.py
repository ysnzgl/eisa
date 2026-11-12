"""Sponsorluk kampanyasi serileştiricileri.

``CampaignSerializer`` / ``CreativeSerializer`` / ``KioskSponsorship*`` yonetim
DTO'lari ve kiosk-edge DTO'lari (``KioskCreativeSyncSerializer``,
``KioskPlaylistSerializer``, ``ProofOfPlay*Serializer``).
"""
from django.conf import settings
import uuid
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.core.media_proxy import media_proxy_url

from .models import (
    Bolge,
    BolgeKapsam,
    Campaign,
    Creative,
    GenerationJob,
    IdleScreenContent,
    KatkiHakedis,
    KioskSponsorship,
    PharmacyCampaign,
    PlayLog,
    Playlist,
    PlaylistItem,
    SponsorTahsilat,
    SponsorlukTarifesi,
)
from .services.sponsorship_engine import hhmm_to_minute


# ─────────────────────────────────────────────────────────────────────────────
# Yardimci — kalici URL'den object_key turetme
# ─────────────────────────────────────────────────────────────────────────────


def _derive_object_key_from_url(media_url: str) -> str:
    if not media_url:
        return ""
    proxy_marker = "/api/media/"
    if proxy_marker in media_url:
        key = media_url.split(proxy_marker, 1)[1].split("?", 1)[0]
        if key and ".." not in key and "//" not in key:
            return key
        return ""
    if "X-Amz-" in media_url or "x-amz-" in media_url:
        return ""
    base = getattr(settings, "S3_PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        return ""
    expected_prefix = f"{base}/"
    if media_url.startswith(expected_prefix):
        key = media_url[len(expected_prefix):]
        if ".." in key or "//" in key:
            return ""
        return key
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# Creative
# ─────────────────────────────────────────────────────────────────────────────


class CreativeSerializer(serializers.ModelSerializer):
    is_grid_compliant = serializers.BooleanField(read_only=True)
    media_url = serializers.CharField(max_length=2048)
    active_media_url = serializers.CharField(max_length=2048, allow_blank=True, required=False)

    _GRID_DURATIONS = frozenset({15, 30, 45, 60})

    class Meta:
        model = Creative
        fields = ["id", "campaign", "media_url", "active_media_url", "duration_seconds", "name",
                  "checksum", "object_key", "active_object_key", "is_grid_compliant"]
        read_only_fields = ("id", "is_grid_compliant")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if instance.object_key:
            data["media_url"] = media_proxy_url(instance.object_key, request)
        if instance.active_object_key:
            data["active_media_url"] = media_proxy_url(instance.active_object_key, request)
        return data

    def validate_duration_seconds(self, value: int) -> int:
        if not 1 <= value <= 60:
            raise serializers.ValidationError("duration_seconds 1..60 arasinda olmalidir.")
        instance = getattr(self, "instance", None)
        if instance and int(instance.duration_seconds) == int(value):
            return value
        if value not in self._GRID_DURATIONS:
            raise serializers.ValidationError(
                f"duration_seconds {value} 15sn grid ile uyumsuz. Izin verilen: 15 / 30 / 45 / 60 saniye."
            )
        return value

    def validate_media_url(self, value: str) -> str:
        if not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("media_url yalnizca http veya https olabilir.")
        return value

    def validate_active_media_url(self, value: str) -> str:
        if value and not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("active_media_url yalnizca http veya https olabilir.")
        return value

    def validate(self, attrs):
        # Standart: sponsorluk başına tek medya kaydı (tam ekran media_url + yarım ekran active_media_url).
        campaign = attrs.get("campaign")
        if self.instance is None and campaign is not None and campaign.creatives.exists():
            raise serializers.ValidationError({
                "campaign": "Sponsorluğun zaten medyası var. Bir sponsorluk en fazla bir tam ekran ve bir yarım ekran medyası alabilir."
            })
        if not attrs.get("object_key"):
            attrs["object_key"] = _derive_object_key_from_url(attrs.get("media_url", ""))
        if not attrs.get("active_object_key") and attrs.get("active_media_url"):
            attrs["active_object_key"] = _derive_object_key_from_url(attrs.get("active_media_url", ""))
        return attrs


# ─────────────────────────────────────────────────────────────────────────────
# Campaign (Sponsorluk)
# ─────────────────────────────────────────────────────────────────────────────


class BolgeKapsamSerializer(serializers.ModelSerializer):
    il_adi = serializers.CharField(source="il.ad", read_only=True)
    ilce_adi = serializers.CharField(source="ilce.ad", read_only=True, default="")

    class Meta:
        model = BolgeKapsam
        fields = ("id", "bolge", "il", "il_adi", "ilce", "ilce_adi")
        read_only_fields = ("bolge",)

    def validate(self, attrs):
        il = attrs.get("il") or getattr(self.instance, "il", None)
        ilce = attrs.get("ilce", getattr(self.instance, "ilce", None))
        if ilce and il and ilce.il_id != il.id:
            raise serializers.ValidationError({"ilce": "İlçe seçilen ile ait olmalıdır."})
        return attrs


class BolgeSerializer(serializers.ModelSerializer):
    kapsamlar = BolgeKapsamSerializer(many=True, required=False)
    gecerlilik_baslangic = serializers.DateField(default=timezone.localdate, required=False)

    class Meta:
        model = Bolge
        fields = ("id", "kod", "ad", "gecerlilik_baslangic", "gecerlilik_bitis",
                  "aktif", "aciklama", "kapsamlar")
        extra_kwargs = {"kod": {"required": False}}

    def validate(self, attrs):
        start = attrs.get("gecerlilik_baslangic", getattr(self.instance, "gecerlilik_baslangic", None))
        end = attrs.get("gecerlilik_bitis", getattr(self.instance, "gecerlilik_bitis", None))
        if start and end and end < start:
            raise serializers.ValidationError({"gecerlilik_bitis": "Bitiş başlangıçtan önce olamaz."})
        scopes = attrs.get("kapsamlar")
        if scopes is None:
            scopes = list(self.instance.kapsamlar.all()) if self.instance else []
            scopes = [{"il": row.il, "ilce": row.ilce} for row in scopes]
        if not scopes:
            raise serializers.ValidationError({"kapsamlar": "En az bir il/ilçe kapsamı gereklidir."})
        seen = []
        for row in scopes:
            il_id, ilce_id = row["il"].pk, row.get("ilce").pk if row.get("ilce") else None
            if any(il_id == old_il and (ilce_id is None or old_ilce is None or ilce_id == old_ilce)
                   for old_il, old_ilce in seen):
                raise serializers.ValidationError({"kapsamlar": "Aynı il/ilçe kapsamı tekrarlanamaz veya ilin tamamıyla çakışamaz."})
            seen.append((il_id, ilce_id))
            if attrs.get("aktif", getattr(self.instance, "aktif", True)):
                qs = BolgeKapsam.objects.filter(il_id=il_id, bolge__aktif=True).exclude(bolge=self.instance)
                if ilce_id:
                    qs = qs.filter(Q(ilce_id=ilce_id) | Q(ilce__isnull=True))
                if end:
                    qs = qs.filter(bolge__gecerlilik_baslangic__lte=end)
                qs = qs.filter(Q(bolge__gecerlilik_bitis__isnull=True) | Q(bolge__gecerlilik_bitis__gte=start))
                if qs.exists():
                    raise serializers.ValidationError({"kapsamlar": "Bu il/ilçe aynı tarihlerde başka bir aktif bölgeye bağlı."})
        return attrs

    def _save_kapsamlar(self, instance, kapsamlar):
        if kapsamlar is None:
            return
        instance.kapsamlar.all().delete()
        for row in kapsamlar:
            BolgeKapsam.objects.create(bolge=instance, **row)

    @transaction.atomic
    def create(self, validated_data):
        kapsamlar = validated_data.pop("kapsamlar", [])
        validated_data.setdefault("kod", "B-" + uuid.uuid4().hex[:20])
        instance = super().create(validated_data)
        self._save_kapsamlar(instance, kapsamlar)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        kapsamlar = validated_data.pop("kapsamlar", None)
        instance = super().update(instance, validated_data)
        self._save_kapsamlar(instance, kapsamlar)
        return instance


class SponsorlukTarifesiSerializer(serializers.ModelSerializer):
    tur_display = serializers.CharField(source="get_tur_display", read_only=True)
    kod = serializers.CharField(required=False, default=lambda: "T-" + uuid.uuid4().hex[:20])

    class Meta:
        model = SponsorlukTarifesi
        fields = ("id", "kod", "ad", "tur", "tur_display", "min_cihaz", "max_cihaz",
                  "brut_bedel", "kdv_orani", "gecerlilik_baslangic",
                  "gecerlilik_bitis", "aktif", "aciklama")
        extra_kwargs = {"kod": {"required": False}}

    def create(self, validated_data):
        validated_data.setdefault("kod", "T-" + uuid.uuid4().hex[:20])
        return super().create(validated_data)

    def validate(self, attrs):
        min_cihaz = attrs.get("min_cihaz", getattr(self.instance, "min_cihaz", 1))
        max_cihaz = attrs.get("max_cihaz", getattr(self.instance, "max_cihaz", None))
        start = attrs.get("gecerlilik_baslangic", getattr(self.instance, "gecerlilik_baslangic", None))
        end = attrs.get("gecerlilik_bitis", getattr(self.instance, "gecerlilik_bitis", None))
        if max_cihaz is not None and max_cihaz < min_cihaz:
            raise serializers.ValidationError({"max_cihaz": "Üst cihaz sınırı alt sınırdan küçük olamaz."})
        if start and end and end < start:
            raise serializers.ValidationError({"gecerlilik_bitis": "Bitiş başlangıçtan önce olamaz."})
        if min_cihaz < 1:
            raise serializers.ValidationError({"min_cihaz": "Alt cihaz sınırı en az 1 olmalıdır."})
        if attrs.get("brut_bedel", getattr(self.instance, "brut_bedel", 0)) < 0:
            raise serializers.ValidationError({"brut_bedel": "Bedel negatif olamaz."})
        if attrs.get("kdv_orani", getattr(self.instance, "kdv_orani", 20)) not in (0, 1, 10, 20):
            raise serializers.ValidationError({"kdv_orani": "Geçersiz KDV oranı."})
        if attrs.get("aktif", getattr(self.instance, "aktif", True)):
            qs = SponsorlukTarifesi.objects.filter(
                kod=attrs.get("kod", getattr(self.instance, "kod", "")), aktif=True,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if end:
                qs = qs.filter(gecerlilik_baslangic__lte=end)
            qs = qs.filter(Q(gecerlilik_bitis__isnull=True) | Q(gecerlilik_bitis__gte=start))
            if qs.exists():
                raise serializers.ValidationError({"gecerlilik_baslangic": "Aynı tarife kodunun geçerlilik tarihleri çakışamaz."})
        return attrs


class CampaignSerializer(serializers.ModelSerializer):
    creatives = CreativeSerializer(many=True, read_only=True)
    effective_state = serializers.SerializerMethodField()
    assigned_kiosk_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id", "advertiser_name", "name", "start_date", "end_date",
            "status", "sponsorluk_tarifesi", "tarife_snapshot", "bolge",
            "effective_state", "creatives", "assigned_kiosk_count",
            "olusturulma_tarihi", "guncellenme_tarihi", "surum",
        ]
        read_only_fields = (
            "id", "tarife_snapshot", "effective_state", "creatives", "assigned_kiosk_count",
            "olusturulma_tarihi", "guncellenme_tarihi", "surum",
        )

    def get_effective_state(self, obj):
        return obj.effective_state

    def get_assigned_kiosk_count(self, obj):
        if hasattr(obj, "_assigned_kiosk_count"):
            return obj._assigned_kiosk_count
        return obj.kiosk_sponsorships.count()

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and start >= end:
            raise serializers.ValidationError({"end_date": "end_date, start_date'ten sonra olmalidir."})
        tarife = attrs.get("sponsorluk_tarifesi", getattr(self.instance, "sponsorluk_tarifesi", None))
        if tarife is None and (self.instance is None or self.instance.sponsorluk_tarifesi_id):
            raise serializers.ValidationError({"sponsorluk_tarifesi": "Yeni kampanyada sponsorluk tarifesi zorunludur."})
        if tarife:
            changed = self.instance is None or self.instance.sponsorluk_tarifesi_id != tarife.pk
            snapshot = self.instance.tarife_snapshot if self.instance and not changed else {}
            if changed and not tarife.aktif:
                raise serializers.ValidationError({"sponsorluk_tarifesi": "Pasif tarife yeni kampanyaya seçilemez."})
            if changed or "start_date" in attrs:
                ref_date = timezone.localtime(start).date()
                validity_start = str(snapshot.get("gecerlilik_baslangic") or tarife.gecerlilik_baslangic)
                validity_end = snapshot.get("gecerlilik_bitis") if snapshot else tarife.gecerlilik_bitis
                if str(ref_date) < validity_start or (validity_end and str(ref_date) > str(validity_end)):
                    raise serializers.ValidationError({"sponsorluk_tarifesi": "Tarife kampanya başlangıcında geçerli değildir."})
            bolge = attrs.get("bolge", getattr(self.instance, "bolge", None))
            if (snapshot.get("tur") or tarife.tur) == SponsorlukTarifesi.Tur.BOLGE and not bolge:
                raise serializers.ValidationError({"bolge": "Bölge tarifesinde bölge seçimi zorunludur."})
            if changed or not snapshot:
                attrs["tarife_snapshot"] = {
                    "id": tarife.id, "kod": tarife.kod, "ad": tarife.ad, "tur": tarife.tur,
                    "min_cihaz": tarife.min_cihaz, "max_cihaz": tarife.max_cihaz,
                    "brut_bedel": str(tarife.brut_bedel), "kdv_orani": tarife.kdv_orani,
                    "gecerlilik_baslangic": str(tarife.gecerlilik_baslangic),
                    "gecerlilik_bitis": str(tarife.gecerlilik_bitis) if tarife.gecerlilik_bitis else None,
                }
        return attrs


class SponsorTahsilatSerializer(serializers.ModelSerializer):
    campaign_ad = serializers.CharField(source="campaign.name", read_only=True)
    hakedis_sayisi = serializers.IntegerField(source="hakedisler.count", read_only=True)

    class Meta:
        model = SponsorTahsilat
        fields = ("id", "campaign", "campaign_ad", "brut_tutar", "tahsilat_tarihi",
                  "donem_baslangic", "donem_bitis", "yontem", "referans", "aciklama",
                  "hakedis_sayisi", "hesaplanma_tarihi", "hesap_ozeti", "olusturulma_tarihi")
        read_only_fields = ("id", "campaign_ad", "hakedis_sayisi", "hesaplanma_tarihi", "hesap_ozeti", "olusturulma_tarihi")

    def validate(self, attrs):
        if self.instance and (self.instance.hesaplanma_tarihi or self.instance.hakedisler.exists()):
            raise serializers.ValidationError("Katkısı hesaplanmış tahsilat değiştirilemez.")
        if attrs.get("brut_tutar", getattr(self.instance, "brut_tutar", 0)) <= 0:
            raise serializers.ValidationError({"brut_tutar": "Tahsilat sıfırdan büyük olmalıdır."})
        start = attrs.get("donem_baslangic", getattr(self.instance, "donem_baslangic", None))
        end = attrs.get("donem_bitis", getattr(self.instance, "donem_bitis", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"donem_bitis": "Dönem bitişi başlangıçtan sonra olmalıdır."})
        if attrs.get("tahsilat_tarihi", getattr(self.instance, "tahsilat_tarihi", timezone.localdate())) > timezone.localdate():
            raise serializers.ValidationError({"tahsilat_tarihi": "Fiili tahsilat tarihi gelecekte olamaz."})
        return attrs


class KatkiHakedisSerializer(serializers.ModelSerializer):
    eczane_ad = serializers.CharField(source="eczane.ad", read_only=True)
    campaign_ad = serializers.CharField(source="tahsilat.campaign.name", read_only=True)
    donem_baslangic = serializers.DateField(source="tahsilat.donem_baslangic", read_only=True)
    donem_bitis = serializers.DateField(source="tahsilat.donem_bitis", read_only=True)

    class Meta:
        model = KatkiHakedis
        fields = ("id", "tahsilat", "campaign_ad", "donem_baslangic", "donem_bitis",
                  "eczane", "eczane_ad", "uygun_cihaz_gun",
                  "toplam_uygun_cihaz_gun", "brut_havuz", "brut_pay", "hesap_detayi",
                  "durum", "bildirim_tarihi", "eczane_fatura_no",
                  "eczane_fatura_teblig_tarihi", "odeme_son_tarihi", "odenme_tarihi")
        read_only_fields = ("id", "tahsilat", "eczane", "uygun_cihaz_gun",
                            "toplam_uygun_cihaz_gun", "brut_havuz", "brut_pay", "hesap_detayi",
                            "bildirim_tarihi", "odeme_son_tarihi")

    def validate(self, attrs):
        import datetime as dt
        teblig = attrs.get("eczane_fatura_teblig_tarihi", getattr(self.instance, "eczane_fatura_teblig_tarihi", None))
        fatura_no = attrs.get("eczane_fatura_no", getattr(self.instance, "eczane_fatura_no", ""))
        odeme = attrs.get("odenme_tarihi", getattr(self.instance, "odenme_tarihi", None))
        if teblig and not fatura_no.strip():
            raise serializers.ValidationError({"eczane_fatura_no": "Tebliğ tarihiyle birlikte eczane fatura numarası gereklidir."})
        if (teblig and teblig > timezone.localdate()) or (odeme and odeme > timezone.localdate()):
            raise serializers.ValidationError("Fiili tebliğ/ödeme tarihi gelecekte olamaz.")
        if odeme and (not teblig or odeme < teblig):
            raise serializers.ValidationError({"odenme_tarihi": "Ödeme, eczane faturası tebliğinden önce kaydedilemez."})
        durum = attrs.get("durum", getattr(self.instance, "durum", None))
        if durum == KatkiHakedis.Durum.ODENDI and not odeme:
            raise serializers.ValidationError({"odenme_tarihi": "Ödendi durumunda ödeme tarihi zorunludur."})
        if odeme and durum != KatkiHakedis.Durum.ODENDI:
            raise serializers.ValidationError({"durum": "Ödeme tarihi girildiğinde durum Ödendi olmalıdır."})
        if self.instance and self.instance.odenme_tarihi:
            raise serializers.ValidationError("Ödenmiş hakediş bu uçtan değiştirilemez.")
        attrs["odeme_son_tarihi"] = teblig + dt.timedelta(days=15) if teblig else None
        return attrs


class KatkiHakedisimSerializer(KatkiHakedisSerializer):
    """Eczaneye yalnız kendi hesabını açar; sponsor kimliği ve iç kayıtlar gösterilmez."""

    class Meta(KatkiHakedisSerializer.Meta):
        fields = ("id", "donem_baslangic", "donem_bitis", "uygun_cihaz_gun",
                  "toplam_uygun_cihaz_gun", "brut_havuz", "brut_pay", "durum",
                  "bildirim_tarihi", "eczane_fatura_no", "eczane_fatura_teblig_tarihi",
                  "odeme_son_tarihi", "odenme_tarihi")
        read_only_fields = fields


# ─────────────────────────────────────────────────────────────────────────────
# KioskSponsorship yonetim DTO'lari
# ─────────────────────────────────────────────────────────────────────────────


def _validate_weekdays(value):
    if value in (None, []):
        return value
    if not isinstance(value, list):
        raise serializers.ValidationError("active_weekdays liste olmalidir.")
    out = []
    for d in value:
        try:
            di = int(d)
        except (TypeError, ValueError):
            raise serializers.ValidationError("active_weekdays ISO 1-7 tamsayilari olmalidir.")
        if not 1 <= di <= 7:
            raise serializers.ValidationError("active_weekdays 1-7 araliginda olmalidir (ISO).")
        out.append(di)
    return out


class _WindowItemMixin:
    """window_start/window_end HH:MM -> dakika donusumu ve dogrulama."""

    def _parse_window(self, window_start: str, window_end: str):
        try:
            s = hhmm_to_minute(window_start)
        except ValueError as exc:
            raise serializers.ValidationError({"window_start": str(exc)})
        try:
            e = hhmm_to_minute(window_end, allow_2400=True)
        except ValueError as exc:
            raise serializers.ValidationError({"window_end": str(exc)})
        if e <= s:
            raise serializers.ValidationError(
                {"window_end": "window_end, window_start'tan sonra olmalidir."}
            )
        return s, e


class KioskSponsorshipItemSerializer(serializers.Serializer, _WindowItemMixin):
    """PUT/assign icin tek atama girdisi (HH:MM pencereli)."""

    campaign_id = serializers.UUIDField()
    window_start = serializers.CharField()
    window_end = serializers.CharField()
    count = serializers.IntegerField(min_value=1)
    active_weekdays = serializers.ListField(required=False, allow_null=True, default=None)
    start_date = serializers.DateField(required=False, allow_null=True, default=None)
    end_date = serializers.DateField(required=False, allow_null=True, default=None)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_active_weekdays(self, value):
        return _validate_weekdays(value)

    def validate(self, attrs):
        s, e = self._parse_window(attrs["window_start"], attrs["window_end"])
        attrs["window_start_minute"] = s
        attrs["window_end_minute"] = e
        sd, ed = attrs.get("start_date"), attrs.get("end_date")
        if sd and ed and sd > ed:
            raise serializers.ValidationError({"end_date": "end_date start_date'ten once olamaz."})
        return attrs


def _minute_to_hhmm(minute: int) -> str:
    minute = int(minute)
    return f"{minute // 60:02d}:{minute % 60:02d}"


class KioskSponsorshipReadSerializer(serializers.ModelSerializer):
    """GET campaigns/{id}/kiosks/ satiri."""

    kiosk_name = serializers.SerializerMethodField()
    eczane_adi = serializers.SerializerMethodField()
    il_adi = serializers.SerializerMethodField()
    ilce_adi = serializers.SerializerMethodField()
    window_start = serializers.SerializerMethodField()
    window_end = serializers.SerializerMethodField()

    class Meta:
        model = KioskSponsorship
        fields = [
            "id", "kiosk_id", "kiosk_name", "eczane_adi", "il_adi", "ilce_adi",
            "window_start", "window_end", "count", "active_weekdays",
            "start_date", "end_date", "is_active",
        ]

    def get_kiosk_name(self, obj):
        return obj.kiosk.ad

    def get_eczane_adi(self, obj):
        return obj.kiosk.eczane.ad if obj.kiosk.eczane_id else ""

    def get_il_adi(self, obj):
        ecz = obj.kiosk.eczane
        return ecz.il.ad if ecz and ecz.il_id else ""

    def get_ilce_adi(self, obj):
        ecz = obj.kiosk.eczane
        return ecz.ilce.ad if ecz and ecz.ilce_id else ""

    def get_window_start(self, obj):
        return _minute_to_hhmm(obj.window_start_minute)

    def get_window_end(self, obj):
        return _minute_to_hhmm(obj.window_end_minute)


# ─────────────────────────────────────────────────────────────────────────────
# IdleScreenContent
# ─────────────────────────────────────────────────────────────────────────────


class IdleScreenContentSerializer(serializers.ModelSerializer):
    """Idle ekrani baslik/metin icerigi (duz metin). HTML calistirilmaz."""

    created_at = serializers.DateTimeField(source="olusturulma_tarihi", read_only=True)
    updated_at = serializers.DateTimeField(source="guncellenme_tarihi", read_only=True)

    class Meta:
        model = IdleScreenContent
        fields = ["id", "baslik", "baslik_en", "metin", "metin_en", "aktif", "kategori", "created_at", "updated_at"]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_baslik(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Baslik zorunludur.")
        if len(value) > 100:
            raise serializers.ValidationError("Baslik en fazla 100 karakter olabilir.")
        return value

    def validate_metin(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Metin zorunludur.")
        if len(value) > 300:
            raise serializers.ValidationError("Metin en fazla 300 karakter olabilir.")
        return value

    def validate_baslik_en(self, value: str) -> str:
        value = (value or "").strip()
        if len(value) > 100:
            raise serializers.ValidationError("Ingilizce baslik en fazla 100 karakter olabilir.")
        return value

    def validate_metin_en(self, value: str) -> str:
        value = (value or "").strip()
        if len(value) > 300:
            raise serializers.ValidationError("Ingilizce metin en fazla 300 karakter olabilir.")
        return value


# ─────────────────────────────────────────────────────────────────────────────
# Kiosk-edge DTO'lari
# ─────────────────────────────────────────────────────────────────────────────


def _kiosk_media_url(request, object_key: str, fallback: str = "") -> str:
    if not object_key:
        return fallback
    rel = f"/api/kiosk/v1/media/{object_key}"
    if request is not None:
        return request.build_absolute_uri(rel)
    return rel


class KioskCreativeSyncSerializer(serializers.ModelSerializer):
    """`/api/kiosk/v1/sync` icindeki tek bir creative."""

    media_url = serializers.SerializerMethodField()
    active_media_url = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()

    class Meta:
        model = Creative
        fields = ["id", "media_url", "active_media_url", "duration_seconds", "checksum", "type"]

    def get_media_url(self, obj):
        return _kiosk_media_url(self.context.get("request"), obj.object_key, obj.media_url)

    def get_active_media_url(self, obj):
        return _kiosk_media_url(self.context.get("request"), obj.active_object_key, obj.active_media_url)

    def get_type(self, obj):  # noqa: D401
        return "creative"


class KioskIdleContentSyncSerializer(serializers.ModelSerializer):
    """`/api/kiosk/v1/sync` icindeki tek bir aktif idle icerigi."""

    updated_at = serializers.DateTimeField(source="guncellenme_tarihi", read_only=True)
    kategori_ikon = serializers.SerializerMethodField()

    class Meta:
        model = IdleScreenContent
        fields = ["id", "baslik", "baslik_en", "metin", "metin_en", "aktif", "kategori_id", "kategori_ikon", "updated_at"]

    def get_kategori_ikon(self, obj):
        return obj.kategori.ikon if obj.kategori_id and obj.kategori else None


class KioskPlaylistItemSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    active_media_url = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    asset_id = serializers.SerializerMethodField()
    asset_type = serializers.SerializerMethodField()
    campaign_name = serializers.SerializerMethodField()

    class Meta:
        model = PlaylistItem
        fields = [
            "id", "asset_id", "asset_type", "campaign_name", "media_url",
            "active_media_url", "duration_seconds", "playback_order",
            "estimated_start_offset_seconds",
        ]

    def get_media_url(self, obj):
        req = self.context.get("request")
        if obj.creative_id:
            return _kiosk_media_url(req, obj.creative.object_key, obj.creative.media_url)
        return None

    def get_active_media_url(self, obj):
        if obj.creative_id:
            return _kiosk_media_url(
                self.context.get("request"), obj.creative.active_object_key, obj.creative.active_media_url,
            )
        return ""

    def get_duration_seconds(self, obj):
        if obj.creative_id:
            return obj.creative.duration_seconds
        return 0

    def get_asset_id(self, obj):
        return str(obj.creative_id) if obj.creative_id else None

    def get_asset_type(self, obj):
        return "creative"

    def get_campaign_name(self, obj):
        if obj.creative_id and obj.creative.campaign_id:
            return obj.creative.campaign.name
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
    play_event_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    status = serializers.ChoiceField(
        choices=["STARTED", "COMPLETED", "FAILED", "INTERRUPTED"],
        default="COMPLETED", required=False,
    )
    expected_duration = serializers.IntegerField(
        min_value=0, max_value=600, required=False, allow_null=True, default=None
    )
    error_code = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    error_summary = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    occurred_at = serializers.DateTimeField(required=False, allow_null=True, default=None)

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
        fields = ["id", "kiosk", "creative", "played_at", "duration_played"]
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


class GenerationJobSerializer(serializers.ModelSerializer):
    progress_pct = serializers.IntegerField(read_only=True)
    job_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = GenerationJob
        fields = [
            "id", "job_id",
            "target_date", "kiosk", "status", "triggered_by",
            "total_kiosks", "done_kiosks", "failed_kiosks", "playlists_generated",
            "progress_pct", "error_detail", "started_at", "finished_at",
            "olusturulma_tarihi",
            "attempt_count", "max_attempts", "available_at", "dedupe_key", "payload",
        ]
        read_only_fields = fields


# ─────────────────────────────────────────────────────────────────────────────
# PharmacyCampaign — eczaci paneli (dokunulmadi)
# ─────────────────────────────────────────────────────────────────────────────


class PharmacyCampaignSerializer(serializers.ModelSerializer):
    """Eczaci paneli kampanyasi — admin CRUD."""

    _ALLOWED_DURATIONS = frozenset({15, 30, 60})
    media_url = serializers.CharField(max_length=2048)

    class Meta:
        model = PharmacyCampaign
        fields = [
            "id", "name", "media_url", "object_key",
            "start_at", "end_at", "duration_seconds",
            "is_active",
            "target_pharmacies", "target_iller", "target_ilceler",
            "olusturulma_tarihi", "guncellenme_tarihi",
        ]
        read_only_fields = ("id", "olusturulma_tarihi", "guncellenme_tarihi")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.object_key:
            data["media_url"] = media_proxy_url(instance.object_key, self.context.get("request"))
        return data

    def validate_duration_seconds(self, value: int) -> int:
        instance = getattr(self, "instance", None)
        if instance and int(instance.duration_seconds) == int(value):
            return value
        if value not in self._ALLOWED_DURATIONS:
            raise serializers.ValidationError(
                f"duration_seconds {value} gecersiz. Izin verilen: 15, 30, 60 saniye."
            )
        return value

    def validate_media_url(self, value: str) -> str:
        if not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("media_url yalnizca http veya https olabilir.")
        return value

    def validate(self, attrs):
        if not attrs.get("object_key") and attrs.get("media_url"):
            derived = _derive_object_key_from_url(attrs["media_url"])
            attrs["object_key"] = derived or None

        is_create = self.instance is None
        is_partial = getattr(self, "partial", False)
        if is_create or not is_partial:
            ph_val = attrs.get("target_pharmacies", [])
            il_val = attrs.get("target_iller", [])
            ilce_val = attrs.get("target_ilceler", [])
            if not ph_val and not il_val and not ilce_val:
                raise serializers.ValidationError(
                    "En az bir hedef secilmelidir: eczane, il veya ilce."
                )
        return attrs


class PharmacyCampaignFeedSerializer(serializers.ModelSerializer):
    """Eczaci feed — yalnizca gosterim icin gereken alanlar."""

    media_url = serializers.SerializerMethodField()

    class Meta:
        model = PharmacyCampaign
        fields = ["id", "name", "media_url", "duration_seconds"]

    def get_media_url(self, obj):
        if obj.object_key:
            return media_proxy_url(obj.object_key, self.context.get("request"))
        return obj.media_url
