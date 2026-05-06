"""Urun/kategori serileştiricileri."""
from rest_framework import serializers

from .models import Cevap, EtkenMadde, Kategori, Soru


class CevapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cevap
        fields = ["id", "metin", "agirlik"]


class SoruSerializer(serializers.ModelSerializer):
    cevaplar = CevapSerializer(many=True, read_only=True)

    class Meta:
        model = Soru
        fields = [
            "id", "kategori", "seed_id", "metin", "sira", "cevaplar",
            "eslesme_kurallari",
            "hedef_cinsiyetler", "hedef_yas_araliklari",
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
            "hedef_cinsiyetler", "hedef_yas_araliklari",
        ]


class SoruDetayliSerializer(serializers.ModelSerializer):
    """Kiosk sync icin: cevaplar ic ice + hedefleme."""

    cevaplar = CevapSerializer(many=True, read_only=True)

    class Meta:
        model = Soru
        fields = [
            "id", "metin", "sira", "cevaplar",
            "hedef_cinsiyetler", "hedef_yas_araliklari",
        ]


class KategoriSyncSerializer(serializers.ModelSerializer):
    """Kiosk sync icin: aktif kategoriler + sorular + cevaplar + hedefleme."""

    sorular = SoruDetayliSerializer(many=True, read_only=True)

    class Meta:
        model = Kategori
        fields = [
            "id", "ad", "slug", "ikon", "hassas", "sorular",
            "hedef_cinsiyetler", "hedef_yas_araliklari",
        ]


class EtkenMaddeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtkenMadde
        fields = ["id", "ad", "aciklama"]
