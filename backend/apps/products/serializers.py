"""Urun/kategori serileştiricileri."""
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import Cevap, Danisma, EtkenMadde, Kategori, Soru, SoruEtkenMadde


class CevapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cevap
        fields = ["id", "metin", "agirlik"]


class CevapWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cevap
        fields = ["id", "soru", "metin", "agirlik"]


class EtkenMaddeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtkenMadde
        fields = ["id", "ad", "aciklama", "aktif"]


class SoruEtkenMaddeSerializer(serializers.ModelSerializer):
    """Soru–EtkenMadde bağlantısı okuma/yazma serializer'ı."""

    etken_madde_ad = serializers.CharField(source="etken_madde.ad", read_only=True)

    class Meta:
        model = SoruEtkenMadde
        fields = ["id", "soru", "etken_madde", "etken_madde_ad", "rol"]
        validators = [
            UniqueTogetherValidator(
                queryset=SoruEtkenMadde.objects.all(),
                fields=["soru", "etken_madde"],
                message="Bu soruya bu etken madde zaten eklenmiş.",
            )
        ]


class SoruSerializer(serializers.ModelSerializer):
    cevaplar = CevapSerializer(many=True, read_only=True)
    hedef_etken_maddeler = SoruEtkenMaddeSerializer(
        many=True, read_only=True, source="etken_madde_baglantilari"
    )

    class Meta:
        model = Soru
        fields = [
            "id", "kategori", "metin", "sira", "cevaplar",
            "hedef_cinsiyet", "hedef_yas_araliklari", "hedef_etken_maddeler",
        ]
        read_only_fields = ("id",)


class KategoriSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kategori
        fields = [
            "id", "ad", "slug", "ikon", "aktif",
            "hedef_cinsiyet", "hedef_yas_araliklari",
            "bagli_kategori",
        ]


class DanismaSerializer(serializers.ModelSerializer):
    ust_kategori_ad = serializers.CharField(source="ust_kategori.ad", read_only=True)

    class Meta:
        model = Danisma
        fields = ["id", "ad", "slug", "ikon", "aktif", "ust_kategori", "ust_kategori_ad"]


class SoruDetayliSerializer(serializers.ModelSerializer):
    """Kiosk sync icin: cevaplar ic ice + hedefleme + eslesme_kurallari."""

    cevaplar = CevapSerializer(many=True, read_only=True)
    hedef_etken_maddeler = SoruEtkenMaddeSerializer(
        many=True, read_only=True, source="etken_madde_baglantilari"
    )
    eslesme_kurallari = serializers.SerializerMethodField()

    def get_eslesme_kurallari(self, obj):
        """ingredients.js'in bekledigi match_rules formatini uretir."""
        em_by_rol = {b.rol: b.etken_madde.ad for b in obj.etken_madde_baglantilari.all()}
        primary = em_by_rol.get(SoruEtkenMadde.ROL_ANA, "")
        if not primary:
            return []
        gender = [obj.hedef_cinsiyet.kod] if obj.hedef_cinsiyet else ["F", "M"]
        yas_objs = list(obj.hedef_yas_araliklari.all())
        if yas_objs:
            age_min = min(y.alt_sinir for y in yas_objs)
            ust_vals = [y.ust_sinir for y in yas_objs if y.ust_sinir is not None]
            age_max = max(ust_vals) if ust_vals else 200
        else:
            age_min, age_max = 0, 200
        return [{
            "gender": gender,
            "age_min": age_min,
            "age_max": age_max,
            "primary": primary,
            "supportive": em_by_rol.get(SoruEtkenMadde.ROL_DESTEKLEYICI, ""),
        }]

    class Meta:
        model = Soru
        fields = [
            "id", "metin", "sira", "cevaplar",
            "hedef_cinsiyet", "hedef_yas_araliklari", "hedef_etken_maddeler",
            "eslesme_kurallari",
        ]


class KategoriSyncSerializer(serializers.ModelSerializer):
    """Kiosk sync icin: aktif kategoriler + sorular + cevaplar + hedefleme."""

    sorular = SoruDetayliSerializer(many=True, read_only=True)

    class Meta:
        model = Kategori
        fields = [
            "id", "ad", "slug", "ikon", "sorular",
            "hedef_cinsiyet", "hedef_yas_araliklari",
            "bagli_kategori",
        ]


class DanismaSyncSerializer(serializers.ModelSerializer):
    """Kiosk sync icin: danisma kategorileri."""

    alt_kategoriler = serializers.SerializerMethodField()

    def get_alt_kategoriler(self, obj):
        return DanismaSyncSerializer(
            obj.alt_kategoriler.filter(aktif=True), many=True
        ).data

    class Meta:
        model = Danisma
        fields = ["id", "ad", "slug", "ikon", "ust_kategori", "alt_kategoriler"]
