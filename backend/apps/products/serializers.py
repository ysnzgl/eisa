"""Urun/kategori serileştiricileri."""
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import Cevap, EtkenMadde, Kategori, Soru, SoruEtkenMadde


class CevapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cevap
        fields = ["id", "metin", "agirlik"]


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


class CevapWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cevap
        fields = ["id", "soru", "metin", "agirlik"]


class KategoriSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kategori
        fields = [
            "id", "ad", "slug", "ikon", "hassas", "aktif",
            "hedef_cinsiyet", "hedef_yas_araliklari",
        ]


class SoruDetayliSerializer(serializers.ModelSerializer):
    """Kiosk sync icin: cevaplar ic ice + hedefleme."""

    cevaplar = CevapSerializer(many=True, read_only=True)
    hedef_etken_maddeler = SoruEtkenMaddeSerializer(
        many=True, read_only=True, source="etken_madde_baglantilari"
    )

    class Meta:
        model = Soru
        fields = [
            "id", "metin", "sira", "cevaplar",
            "hedef_cinsiyet", "hedef_yas_araliklari", "hedef_etken_maddeler",
        ]


class KategoriSyncSerializer(serializers.ModelSerializer):
    """Kiosk sync icin: aktif kategoriler + sorular + cevaplar + hedefleme."""

    sorular = SoruDetayliSerializer(many=True, read_only=True)

    class Meta:
        model = Kategori
        fields = [
            "id", "ad", "slug", "ikon", "hassas", "sorular",
            "hedef_cinsiyet", "hedef_yas_araliklari",
        ]

