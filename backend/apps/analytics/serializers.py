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
    kategori_slug = serializers.SlugField()
    hassas_akis = serializers.BooleanField(default=False)
    qr_kodu = serializers.CharField(max_length=64)
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
    cevap_detaylari = serializers.SerializerMethodField()
    onerilen_etken_madde_detaylari = serializers.SerializerMethodField()
    satis_sonucu = serializers.SerializerMethodField()
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
            "kategori",
            "kategori_adi",
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
            "satis_sonucu",
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

    def get_onerilen_etken_madde_detaylari(self, obj):
        if not self._include_detail_fields():
            return []

        values = obj.onerilen_etken_maddeler
        if not isinstance(values, list) or not values:
            return []

        ids = []
        for value in values:
            if isinstance(value, dict):
                parsed = self._parse_int(value.get("id"))
            else:
                parsed = self._parse_int(value)
            if parsed is not None:
                ids.append(parsed)

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

    def get_satis_sonucu(self, obj):
        value = self.context.get("sale_result")
        if value == "sold":
            return "Satış yapıldı"
        if value == "not_sold":
            return "Satış yapılmadı"
        return None
