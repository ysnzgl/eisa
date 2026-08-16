"""Analitik serileştiricileri."""
import re

from rest_framework import serializers

from apps.lookups.models import Cinsiyet, YasAraligi
from apps.products.models import Cevap, EtkenMadde, Soru

from .models import OturumLogu


class OturumLoguItemSerializer(serializers.Serializer):
    """
    Kiosk'tan gelen tek oturum kaydi. yas_araligi_kod ve cinsiyet_kod string olarak gelir;
    server lookup'a cevirir. category_slug Kategori.slug ile eslesir.
    """

    idempotency_anahtari = serializers.UUIDField()
    kiosk_mac = serializers.CharField(max_length=17, required=False, allow_blank=True)
    yas_araligi_kod = serializers.CharField(max_length=8)
    cinsiyet_kod = serializers.CharField(max_length=4)
    oturum_tipi = serializers.ChoiceField(
        choices=["SIKAYET", "OZEL_DANISMANLIK"], default="SIKAYET"
    )
    kategori_slug = serializers.SlugField(required=False, allow_null=True, allow_blank=True)
    danisma_kategorisi_id = serializers.IntegerField(required=False, allow_null=True)
    danisma_kategorisi_slug = serializers.SlugField(required=False, allow_null=True, allow_blank=True)
    hassas_akis = serializers.BooleanField(default=False)
    # qr_kodu: backend generates it — client value is IGNORED.
    # Field kept optional so existing edge code sending qr_kodu doesn't break.
    qr_kodu = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)
    cevaplar = serializers.JSONField(default=dict)
    onerilen_etken_maddeler = serializers.JSONField(default=list)
    tamamlandi = serializers.BooleanField(default=True)
    olusturulma_tarihi = serializers.DateTimeField(required=False, allow_null=True)
    danisma_tamamlandi = serializers.BooleanField(default=False)
    danisma_tamamlanma_tarihi = serializers.DateTimeField(required=False, allow_null=True)
    danisma_notu = serializers.CharField(max_length=500, required=False, allow_blank=True)
    danisma_tamamlayan_eczaci = serializers.CharField(
        source="danisma_tamamlayan_eczaci.get_full_name", read_only=True, default=""
    )
    # Fişte basılan barkod logosu ID'si (UUID). Null = e-ISA fallback.
    # Eski kiosk payload'larında bu alan bulunmayabilir; geriye dönük uyumluluk için opsiyoneldir.
    barkod_logo_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class OturumLoguSerializer(serializers.ModelSerializer):
    kategori_adi = serializers.CharField(source="kategori.ad", read_only=True)
    kiosk_mac = serializers.CharField(source="kiosk.mac_adresi", read_only=True)
    eczane_adi = serializers.CharField(source="kiosk.eczane.ad", read_only=True)
    yas_araligi_kod = serializers.CharField(source="yas_araligi.kod", read_only=True)
    cinsiyet_kod = serializers.CharField(source="cinsiyet.kod", read_only=True)
    qr_code = serializers.CharField(source="qr_kodu", read_only=True)
    kiosk_detay = serializers.SerializerMethodField()
    eczane = serializers.SerializerMethodField()
    yas_araligi_detay = serializers.SerializerMethodField()
    cinsiyet_detay = serializers.SerializerMethodField()
    kategori_detay = serializers.SerializerMethodField()
    danisma_kategorisi_detay = serializers.SerializerMethodField()
    cevap_detaylari = serializers.SerializerMethodField()
    onerilen_etken_madde_detaylari = serializers.SerializerMethodField()
    danisma_tamamlayan_eczaci_adi = serializers.CharField(
        source="danisma_tamamlayan_eczaci.get_full_name", read_only=True, default=""
    )

    class Meta:
        model = OturumLogu
        fields = [
            "id",
            "kiosk",
            "kiosk_mac",
            "eczane_adi",
            "yas_araligi",
            "yas_araligi_kod",
            "cinsiyet",
            "cinsiyet_kod",
            "oturum_tipi",
            "kategori",
            "kategori_adi",
            "danisma_kategorisi",
            "hassas_akis",
            "qr_kodu",
            "qr_code",
            "cevaplar",
            "cevap_detaylari",
            "onerilen_etken_maddeler",
            "onerilen_etken_madde_detaylari",
            "tamamlandi",
            "olusturulma_tarihi",
            "kiosk_detay",
            "eczane",
            "yas_araligi_detay",
            "cinsiyet_detay",
            "kategori_detay",
            "danisma_kategorisi_detay",
            "sold",
            "danisma_tamamlandi",
            "danisma_tamamlanma_tarihi",
            "danisma_notu",
            "danisma_tamamlayan_eczaci",
            "danisma_tamamlayan_eczaci_adi",
        ]
        read_only_fields = [
            "danisma_tamamlandi",
            "danisma_tamamlanma_tarihi",
            "danisma_tamamlayan_eczaci",
        ]

    def _include_detail_fields(self) -> bool:
        return bool(self.context.get("include_detail_fields", False))

    @staticmethod
    def _parse_int(value):
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            v = value.strip()
            if not v:
                return None
            if v.isdigit():
                return int(v)
            m = re.search(r"(\d+)$", v)
            if m:
                return int(m.group(1))
        return None

    def _normalize_answer_pairs(self, raw_answers):
        pairs = []
        if isinstance(raw_answers, dict):
            for question_key, answer_value in raw_answers.items():
                qid = self._parse_int(question_key)
                if isinstance(answer_value, dict):
                    aid = self._parse_int(
                        answer_value.get("cevap_id")
                        or answer_value.get("answer_id")
                        or answer_value.get("cevap")
                    )
                    avalue = answer_value.get("cevap") or answer_value.get("answer")
                else:
                    aid = self._parse_int(answer_value)
                    avalue = answer_value
                pairs.append({
                    "question_key": question_key,
                    "question_id": qid,
                    "answer_id": aid,
                    "answer_value": avalue,
                })
        elif isinstance(raw_answers, list):
            for item in raw_answers:
                if not isinstance(item, dict):
                    continue
                question_key = item.get("soru_id") or item.get("question_id") or item.get("soru")
                qid = self._parse_int(question_key)
                aid = self._parse_int(item.get("cevap_id") or item.get("answer_id") or item.get("cevap"))
                avalue = item.get("cevap") or item.get("answer")
                pairs.append({
                    "question_key": question_key,
                    "question_id": qid,
                    "answer_id": aid,
                    "answer_value": avalue,
                })
        return pairs

    @staticmethod
    def _answer_text_from_value(value):
        if isinstance(value, str):
            upper = value.upper()
            if upper == "Y":
                return "Evet"
            if upper == "N":
                return "Hayır"
            return value
        if value is None:
            return "-"
        return str(value)

    def get_kiosk_detay(self, obj):
        kiosk = getattr(obj, "kiosk", None)
        if not kiosk:
            return None
        return {
            "id": kiosk.id,
            "ad": getattr(kiosk, "ad", "") or "",
            "mac_adresi": getattr(kiosk, "mac_adresi", "") or "",
        }

    def get_eczane(self, obj):
        kiosk = getattr(obj, "kiosk", None)
        eczane = getattr(kiosk, "eczane", None) if kiosk else None
        if not eczane:
            return None
        return {
            "id": eczane.id,
            "ad": getattr(eczane, "ad", "") or "",
        }

    def get_yas_araligi_detay(self, obj):
        age = getattr(obj, "yas_araligi", None)
        if not age:
            return None
        return {
            "id": age.id,
            "kod": getattr(age, "kod", "") or "",
            "ad": getattr(age, "ad", "") or "",
        }

    def get_cinsiyet_detay(self, obj):
        gender = getattr(obj, "cinsiyet", None)
        if not gender:
            return None
        return {
            "id": gender.id,
            "kod": getattr(gender, "kod", "") or "",
            "ad": getattr(gender, "ad", "") or "",
        }

    def get_kategori_detay(self, obj):
        category = getattr(obj, "kategori", None)
        if not category:
            return None
        return {
            "id": category.id,
            "ad": getattr(category, "ad", "") or "",
            "slug": getattr(category, "slug", "") or "",
        }

    def get_danisma_kategorisi_detay(self, obj):
        danisma = getattr(obj, "danisma_kategorisi", None)
        if not danisma:
            return None
        return {
            "id": danisma.id,
            "ad": getattr(danisma, "ad", "") or "",
            "slug": getattr(danisma, "slug", "") or "",
        }

    def get_cevap_detaylari(self, obj):
        if not self._include_detail_fields():
            return []

        pairs = self._normalize_answer_pairs(obj.cevaplar)
        if not pairs:
            return []

        question_ids = [p["question_id"] for p in pairs if p["question_id"] is not None]
        answer_ids = [p["answer_id"] for p in pairs if p["answer_id"] is not None]

        question_rows = {
            row["id"]: row
            for row in Soru.objects.filter(id__in=question_ids).values("id", "metin", "sira")
        }
        answer_rows = {
            row["id"]: row
            for row in Cevap.objects.filter(id__in=answer_ids).values("id", "metin")
        }

        details = []
        for idx, pair in enumerate(pairs, start=1):
            qid = pair["question_id"]
            aid = pair["answer_id"]
            qrow = question_rows.get(qid) if qid is not None else None
            arow = answer_rows.get(aid) if aid is not None else None
            question_label = qrow["metin"] if qrow else f"Soru #{qid}" if qid is not None else str(pair["question_key"])
            answer_label = (
                arow["metin"]
                if arow
                else f"Cevap #{aid}" if aid is not None else self._answer_text_from_value(pair["answer_value"])
            )
            details.append(
                {
                    "soru_id": qid,
                    "soru_metni": question_label,
                    "cevap_id": aid,
                    "cevap_metni": answer_label,
                    "sira": qrow["sira"] if qrow and qrow.get("sira") is not None else idx,
                }
            )

        details.sort(key=lambda item: (item.get("sira") or 0, item.get("soru_id") or 0))
        return details

    def _resolve_etken_madde_list(self, values):
        if not isinstance(values, list) or not values:
            return []

        ids = [
            self._parse_int(v.get("id") if isinstance(v, dict) else v)
            for v in values
        ]
        ids = [i for i in ids if i is not None]
        ingredient_rows = {
            row["id"]: row["ad"]
            for row in EtkenMadde.objects.filter(id__in=ids).values("id", "ad")
        }

        details = []
        for value in values:
            if isinstance(value, dict):
                parsed = self._parse_int(value.get("id"))
                name = value.get("ad")
                if parsed is not None:
                    details.append({"id": parsed, "ad": ingredient_rows.get(parsed, name or f"Etken Madde #{parsed}")})
                elif name:
                    details.append({"id": None, "ad": str(name)})
                continue
            parsed = self._parse_int(value)
            if parsed is not None:
                details.append({"id": parsed, "ad": ingredient_rows.get(parsed, f"Etken Madde #{parsed}")})
            else:
                details.append({"id": None, "ad": str(value)})
        return details

    def get_onerilen_etken_madde_detaylari(self, obj):
        if not self._include_detail_fields():
            return []
        # Prefer normalized table rows (include satildi flag)
        records = list(obj.onerilen_etken_madde_detaylari.select_related("etken_madde").all())
        if records:
            return [
                {
                    "id": r.etken_madde_id,
                    "ad": r.etken_madde.ad if r.etken_madde else r.etken_madde_adi_snapshot,
                    "satildi": r.satildi,
                }
                for r in records
            ]
        # Fallback to JSON field for pre-normalization sessions
        return self._resolve_etken_madde_list(obj.onerilen_etken_maddeler)

    def get_satis_sonucu(self, obj):
        if obj.sold is True:
            return "Satış yapıldı"
        if obj.sold is False:
            return "Satış yapılmadı"
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Kiosk Hareketleri — liste görünümü (ham cevap yok, PII maskelendi)
# ─────────────────────────────────────────────────────────────────────────────

class KioskActivityListSerializer(serializers.ModelSerializer):
    """Oturum listesi için hafif serializer. Ham cevaplar gösterilmez."""

    kiosk_ad = serializers.CharField(source="kiosk.ad", read_only=True)
    kiosk_mac = serializers.CharField(source="kiosk.mac_adresi", read_only=True)
    eczane_adi = serializers.CharField(source="kiosk.eczane.ad", read_only=True)
    eczane_id = serializers.IntegerField(source="kiosk.eczane_id", read_only=True)
    yas_araligi_ad = serializers.CharField(source="yas_araligi.ad", read_only=True)
    cinsiyet_ad = serializers.CharField(source="cinsiyet.ad", read_only=True)
    kategori_adi = serializers.CharField(source="kategori.ad", read_only=True)
    danisma_kategorisi_adi = serializers.CharField(
        source="danisma_kategorisi.ad", read_only=True
    )
    # Satış görünümünde prefetch_related ile doldurulur; aksi hâlde boş liste döner.
    etken_madde_adlari = serializers.SerializerMethodField()
    etken_madde_detaylari = serializers.SerializerMethodField()

    def get_etken_madde_adlari(self, obj):
        if not self.context.get("include_ingredients"):
            return []
        return [
            (r.etken_madde.ad if r.etken_madde else r.etken_madde_adi_snapshot)
            for r in obj.onerilen_etken_madde_detaylari.all()
            if r.etken_madde or r.etken_madde_adi_snapshot
        ]

    def get_etken_madde_detaylari(self, obj):
        """Satış görünümü için etken madde detayları (ad + satildi flag)."""
        if not self.context.get("include_ingredients"):
            return []
        return [
            {
                "ad": r.etken_madde.ad if r.etken_madde else r.etken_madde_adi_snapshot,
                "satildi": r.satildi,
            }
            for r in obj.onerilen_etken_madde_detaylari.all()
            if r.etken_madde or r.etken_madde_adi_snapshot
        ]

    class Meta:
        model = OturumLogu
        fields = [
            "id",
            "qr_kodu",
            "durum",
            "oturum_tipi",
            "kiosk",
            "kiosk_ad",
            "kiosk_mac",
            "eczane_id",
            "eczane_adi",
            "yas_araligi_ad",
            "cinsiyet_ad",
            "kategori_adi",
            "danisma_kategorisi_adi",
            "hassas_akis",
            "tamamlandi",
            "danisma_tamamlandi",
            "danisma_tamamlanma_tarihi",
            "danisma_notu",
            "sold",
            "etken_madde_adlari",
            "etken_madde_detaylari",
            "olusturulma_tarihi",
            "cihaz_zamani",
            "sunucu_zamani",
        ]
        # cevaplar ve onerilen_etken_maddeler listede açıklanmaz — detay view'dan alınır.


# ─────────────────────────────────────────────────────────────────────────────
# Kampanya Gösterimleri — PlayLog listesi
# ─────────────────────────────────────────────────────────────────────────────

class CampaignImpressionSerializer(serializers.Serializer):
    """PlayLog kayıtları için serializer (Faz 3'te status/error alanları eklenir)."""

    id = serializers.UUIDField(read_only=True)
    kiosk_id = serializers.IntegerField(read_only=True)
    kiosk_ad = serializers.CharField(source="kiosk.ad", read_only=True)
    kiosk_mac = serializers.CharField(source="kiosk.mac_adresi", read_only=True)
    eczane_id = serializers.IntegerField(source="kiosk.eczane_id", read_only=True)
    eczane_adi = serializers.CharField(source="kiosk.eczane.ad", read_only=True)
    creative_id = serializers.UUIDField(read_only=True)
    creative_adi = serializers.SerializerMethodField()
    campaign_id = serializers.SerializerMethodField()
    campaign_adi = serializers.SerializerMethodField()
    played_at = serializers.DateTimeField(read_only=True)
    duration_played = serializers.IntegerField(read_only=True)

    def get_creative_adi(self, obj):
        return getattr(obj.creative, "name", None) if obj.creative_id else None

    def get_campaign_id(self, obj):
        if obj.creative_id and obj.creative:
            return str(obj.creative.campaign_id)
        return None

    def get_campaign_adi(self, obj):
        if obj.creative_id and obj.creative and obj.creative.campaign_id:
            return getattr(obj.creative.campaign, "name", None)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Faz 4 — KioskEvent serializer
# ─────────────────────────────────────────────────────────────────────────────

class KioskEventSerializer(serializers.ModelSerializer):
    """KioskEvent listesi için serializer (context JSON açılmaz — sanitize edilmiş message yeterli)."""

    kiosk_ad = serializers.CharField(source="kiosk.ad", read_only=True)
    kiosk_mac = serializers.CharField(source="kiosk.mac_adresi", read_only=True)
    eczane_id = serializers.IntegerField(source="kiosk.eczane_id", read_only=True)
    eczane_adi = serializers.CharField(source="kiosk.eczane.ad", read_only=True)

    class Meta:
        from apps.analytics.models import KioskEvent as _KE
        model = _KE
        fields = [
            "id",
            "kiosk",
            "kiosk_ad",
            "kiosk_mac",
            "eczane_id",
            "eczane_adi",
            "event_type",
            "severity",
            "message",
            "occurred_at",
            "received_at",
            "olusturulma_tarihi",
        ]
