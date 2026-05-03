"""Analitik serileştiricileri."""
from rest_framework import serializers

from apps.lookups.models import Cinsiyet, YasAraligi

from .models import OturumLogu, ReklamGosterim


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
    olusturulma_tarihi = serializers.DateTimeField(required=False, allow_null=True)


class ReklamGosterimItemSerializer(serializers.Serializer):
    """Kiosk'tan gelen tek reklam gosterim kaydi."""

    idempotency_anahtari = serializers.UUIDField()
    reklam_id = serializers.IntegerField()
    gosterilme_tarihi = serializers.DateTimeField()
    sure_ms = serializers.IntegerField(min_value=0, default=0)


class OturumLoguSerializer(serializers.ModelSerializer):
    kategori_adi = serializers.CharField(source="kategori.ad", read_only=True)
    kiosk_mac = serializers.CharField(source="kiosk.mac_adresi", read_only=True)
    eczane_adi = serializers.CharField(source="kiosk.eczane.ad", read_only=True)
    yas_araligi_kod = serializers.CharField(source="yas_araligi.kod", read_only=True)
    cinsiyet_kod = serializers.CharField(source="cinsiyet.kod", read_only=True)

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
            "cevaplar",
            "onerilen_etken_maddeler",
            "olusturulma_tarihi",
        ]
