"""Reklam (kampanya) serileştiricisi."""
from rest_framework import serializers

from .models import Reklam


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
