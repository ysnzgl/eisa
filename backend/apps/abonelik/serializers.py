"""Abonelik API serializer'ları."""
from __future__ import annotations

from rest_framework import serializers

from .models import (
    CihazOdemePlani,
    Fatura,
    FiyatTanimi,
    Odeme,
    Sozlesme,
    SozlesmeTalebi,
    SozlesmeUzatma,
)


class FiyatTanimiSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiyatTanimi
        fields = (
            "id", "abonelik_bedeli", "cihaz_kira_bedeli",
            "gecerlilik_baslangic", "aciklama", "olusturulma_tarihi",
        )
        read_only_fields = ("id", "olusturulma_tarihi")

    def validate_abonelik_bedeli(self, v):
        if v is None or v < 0:
            raise serializers.ValidationError("Abonelik bedeli 0 veya üzeri olmalı.")
        return v

    def validate_cihaz_kira_bedeli(self, v):
        if v is None or v < 0:
            raise serializers.ValidationError("Cihaz kira bedeli 0 veya üzeri olmalı.")
        return v


class CihazOdemePlaniSerializer(serializers.ModelSerializer):
    toplam_tutar = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    taksit_tutari = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    durum_display = serializers.CharField(source="get_durum_display", read_only=True)

    class Meta:
        model = CihazOdemePlani
        fields = (
            "id", "sozlesme", "pesin_fiyat", "vade_farki_orani", "taksit_sayisi",
            "baslangic_tarihi", "durum", "durum_display",
            "toplam_tutar", "taksit_tutari",
        )
        read_only_fields = ("sozlesme",)

    def validate(self, attrs):
        # Partial update'te mevcut instance değerlerini tabana al.
        taksit = attrs.get("taksit_sayisi")
        if taksit is None and self.instance is not None:
            taksit = self.instance.taksit_sayisi
        vade = attrs.get("vade_farki_orani")
        if vade is None and self.instance is not None:
            vade = self.instance.vade_farki_orani
        # Peşin (1 taksit) dışında vade farkı zorunlu.
        if taksit and int(taksit) != 1 and (vade is None or vade <= 0):
            raise serializers.ValidationError({
                "vade_farki_orani": "1 aydan fazla taksitte vade farkı zorunludur (> %0)."
            })
        return attrs


class SozlesmeSerializer(serializers.ModelSerializer):
    eczane_ad = serializers.CharField(source="eczane.ad", read_only=True)
    toplam_ay = serializers.IntegerField(read_only=True)
    toplam_gun = serializers.IntegerField(read_only=True)
    kalan_gun = serializers.IntegerField(read_only=True)
    suresi_doldu = serializers.BooleanField(read_only=True)
    etkin_durum = serializers.CharField(read_only=True)
    kullanim_bedeli_baslangic = serializers.DateField(read_only=True)
    bitis_tarihi = serializers.DateField(read_only=True)
    tur_display = serializers.CharField(source="get_tur_display", read_only=True)
    tip_display = serializers.CharField(source="get_sozlesme_tipi_ay_display", read_only=True)
    durum_display = serializers.CharField(source="get_durum_display", read_only=True)
    cihaz_plani = CihazOdemePlaniSerializer(read_only=True)

    class Meta:
        model = Sozlesme
        fields = (
            "id", "eczane", "eczane_ad", "tur", "tur_display",
            "sozlesme_tipi_ay", "tip_display", "demo_gun",
            "baslangic_tarihi", "oteleme_ay", "aylik_kullanim_bedeli",
            "cihaz_durumu", "cihaz_kira_bedeli",
            "ek_ay_toplam", "ek_gun_toplam", "onceki_sozlesme",
            "durum", "durum_display", "notlar",
            "toplam_ay", "toplam_gun", "kalan_gun", "suresi_doldu", "etkin_durum",
            "kullanim_bedeli_baslangic", "bitis_tarihi",
            "cihaz_plani",
        )
        read_only_fields = ("ek_ay_toplam", "ek_gun_toplam")

    def validate(self, attrs):
        tur = attrs.get("tur") or getattr(self.instance, "tur", Sozlesme.Tur.STANDART)
        tip = attrs.get("sozlesme_tipi_ay", getattr(self.instance, "sozlesme_tipi_ay", None))
        demo_gun = attrs.get("demo_gun", getattr(self.instance, "demo_gun", None))
        cihaz_durumu = attrs.get("cihaz_durumu", getattr(self.instance, "cihaz_durumu", Sozlesme.CihazDurum.SATILIK))
        cihaz_kira_bedeli = attrs.get("cihaz_kira_bedeli", getattr(self.instance, "cihaz_kira_bedeli", None))

        if tur == Sozlesme.Tur.DEMO:
            if not demo_gun or int(demo_gun) < 1 or int(demo_gun) > Sozlesme.DEMO_MAKS_GUN:
                raise serializers.ValidationError({
                    "demo_gun": f"Demo süresi 1–{Sozlesme.DEMO_MAKS_GUN} gün olmalıdır."
                })
            attrs["sozlesme_tipi_ay"] = None
        else:
            if tip not in (12, 24, 36):
                raise serializers.ValidationError({
                    "sozlesme_tipi_ay": "Standart sözleşmede süre 12, 24 veya 36 ay olmalıdır."
                })
            attrs["demo_gun"] = None

        if cihaz_durumu == Sozlesme.CihazDurum.KIRALIK:
            if cihaz_kira_bedeli is None or float(cihaz_kira_bedeli) <= 0:
                raise serializers.ValidationError({
                    "cihaz_kira_bedeli": "Kiralık cihaz için kira bedeli girilmelidir."
                })
        else:
            attrs["cihaz_kira_bedeli"] = "0.00"
        return attrs


class SozlesmeUzatmaSerializer(serializers.ModelSerializer):
    olusturan_adi = serializers.CharField(source="olusturan.username", read_only=True, default="")

    class Meta:
        model = SozlesmeUzatma
        fields = ("id", "sozlesme", "ek_ay", "ek_gun", "is_iptal",
                  "neden", "iptal_nedeni", "olusturan_adi", "olusturulma_tarihi")
        read_only_fields = fields


class SozlesmeUzatSerializer(serializers.Serializer):
    """Sözleşme uzatma isteği gövdesi."""

    ek_ay = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    ek_gun = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    neden = serializers.CharField(required=False, allow_blank=True, default="")



class FaturaSerializer(serializers.ModelSerializer):
    eczane_ad = serializers.CharField(source="eczane.ad", read_only=True)
    tip_display = serializers.CharField(source="get_tip_display", read_only=True)
    durum_display = serializers.CharField(source="get_durum_display", read_only=True)

    class Meta:
        model = Fatura
        fields = (
            "id", "eczane", "eczane_ad", "sozlesme", "cihaz_plani",
            "tip", "tip_display", "donem", "taksit_no", "tutar",
            "vade_tarihi", "durum", "durum_display", "odenme_tarihi", "aciklama",
        )
        read_only_fields = fields


class OdemeSerializer(serializers.ModelSerializer):
    yontem_display = serializers.CharField(source="get_yontem_display", read_only=True)
    fatura_donem = serializers.CharField(source="fatura.donem", read_only=True)
    fatura_tip = serializers.CharField(source="fatura.get_tip_display", read_only=True)
    eczane_ad = serializers.CharField(source="fatura.eczane.ad", read_only=True)

    class Meta:
        model = Odeme
        fields = ("id", "fatura", "fatura_donem", "fatura_tip", "eczane_ad",
                  "tutar", "yontem", "yontem_display", "odeme_tarihi")
        read_only_fields = ("id", "tutar", "odeme_tarihi")


class OdemeYapSerializer(serializers.Serializer):
    """'Ödeme Yap' isteği gövdesi (mock tahsilat)."""

    yontem = serializers.ChoiceField(
        choices=Odeme.Yontem.choices, default=Odeme.Yontem.KREDI_KARTI
    )


class SozlesmeTalebiSerializer(serializers.ModelSerializer):
    eczane_ad = serializers.CharField(source="eczane.ad", read_only=True)
    tip_display = serializers.CharField(source="get_talep_tipi_display", read_only=True)
    durum_display = serializers.CharField(source="get_durum_display", read_only=True)

    class Meta:
        model = SozlesmeTalebi
        fields = (
            "id", "eczane", "eczane_ad", "talep_tipi", "tip_display",
            "durum", "durum_display", "hedef_sozlesme",
            "istenen_tur", "istenen_tip_ay", "istenen_demo_gun", "ek_ay", "ek_gun",
            "aciklama", "red_nedeni", "karar_tarihi", "olusan_sozlesme",
            "olusturulma_tarihi",
        )
        read_only_fields = fields


class SozlesmeTalebiCreateSerializer(serializers.ModelSerializer):
    """Eczacının talep oluşturma gövdesi."""

    class Meta:
        model = SozlesmeTalebi
        fields = (
            "talep_tipi", "hedef_sozlesme",
            "istenen_tur", "istenen_tip_ay", "istenen_demo_gun", "ek_ay", "ek_gun",
            "aciklama",
        )

    def validate(self, attrs):
        tip = attrs.get("talep_tipi")
        if tip == SozlesmeTalebi.Tip.YENI:
            if attrs.get("istenen_tur") == Sozlesme.Tur.DEMO:
                g = attrs.get("istenen_demo_gun")
                if not g or g < 1 or g > Sozlesme.DEMO_MAKS_GUN:
                    raise serializers.ValidationError(
                        {"istenen_demo_gun": f"Demo 1–{Sozlesme.DEMO_MAKS_GUN} gün olmalı."})
            elif attrs.get("istenen_tur") == Sozlesme.Tur.STANDART:
                if attrs.get("istenen_tip_ay") not in (12, 24, 36):
                    raise serializers.ValidationError(
                        {"istenen_tip_ay": "Süre 12, 24 veya 36 ay olmalı."})
            else:
                raise serializers.ValidationError({"istenen_tur": "Sözleşme türü seçin."})
        elif tip == SozlesmeTalebi.Tip.UZATMA:
            if not attrs.get("hedef_sozlesme"):
                raise serializers.ValidationError({"hedef_sozlesme": "Uzatılacak sözleşme gerekli."})
            if not (attrs.get("ek_ay") or attrs.get("ek_gun")):
                raise serializers.ValidationError({"ek_ay": "Ek süre (ay/gün) gerekli."})
        elif tip == SozlesmeTalebi.Tip.IPTAL:
            if not attrs.get("hedef_sozlesme"):
                raise serializers.ValidationError({"hedef_sozlesme": "İptal edilecek sözleşme gerekli."})
        return attrs


class TalepKararSerializer(serializers.Serializer):
    """Admin talep kararı (YENI onayında tam sözleşme detayı girilebilir)."""

    onayla = serializers.BooleanField()
    red_nedeni = serializers.CharField(required=False, allow_blank=True, default="")
    istenen_tur = serializers.ChoiceField(choices=Sozlesme.Tur.choices, required=False, allow_blank=True)
    istenen_tip_ay = serializers.IntegerField(required=False, allow_null=True)
    istenen_demo_gun = serializers.IntegerField(required=False, allow_null=True)
    ek_ay = serializers.IntegerField(required=False, allow_null=True)
    ek_gun = serializers.IntegerField(required=False, allow_null=True)
    aciklama = serializers.CharField(required=False, allow_blank=True, default="")
    # YENI onayında sözleşme detayları
    baslangic_tarihi = serializers.DateField(required=False, allow_null=True)
    oteleme_ay = serializers.IntegerField(required=False, allow_null=True)
    aylik_kullanim_bedeli = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True)
    cihaz_durumu = serializers.ChoiceField(
        choices=Sozlesme.CihazDurum.choices, required=False, allow_blank=True)
    cihaz_kira_bedeli = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True)
    pesin_fiyat = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True)
    vade_farki_orani = serializers.DecimalField(
        max_digits=6, decimal_places=2, required=False, allow_null=True)
    taksit_sayisi = serializers.IntegerField(required=False, allow_null=True)
    cihaz_baslangic_tarihi = serializers.DateField(required=False, allow_null=True)
    notlar = serializers.CharField(required=False, allow_blank=True, default="")

