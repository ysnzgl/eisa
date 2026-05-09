"""Reklam (kampanya) serileştiricisi."""
from rest_framework import serializers

from .models import Reklam, ReklamTakvim


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
