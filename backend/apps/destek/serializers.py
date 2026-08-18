"""Görüş ve Destek serializer'ları."""
from rest_framework import serializers

from apps.pharmacies.models import Kiosk

from .models import DestekParametresi, DestekTalebi, DestekYorumu


class DestekParametresiSerializer(serializers.ModelSerializer):
    class Meta:
        model = DestekParametresi
        fields = ["id", "grup", "kod", "ad", "ust_parametre_id", "sira"]


# ── Yorum serializer'ları ──────────────────────────────────────────────────────

class DestekYorumuSerializer(serializers.ModelSerializer):
    yazar_adi = serializers.SerializerMethodField()
    yazar_rol = serializers.SerializerMethodField()

    class Meta:
        model = DestekYorumu
        fields = ["id", "yorum_metni", "olusturulma_tarihi", "yazar_adi", "yazar_rol"]
        read_only_fields = ["id", "olusturulma_tarihi", "yazar_adi", "yazar_rol"]

    def get_yazar_adi(self, obj):
        u = obj.olusturan
        if not u:
            return "—"
        return u.get_full_name() or u.username

    def get_yazar_rol(self, obj):
        return getattr(obj.olusturan, "rol", "pharmacist") if obj.olusturan else "pharmacist"


# ── Ticket list serializer ─────────────────────────────────────────────────────

class DestekTalebiListSerializer(serializers.ModelSerializer):
    eczane_adi = serializers.CharField(source="eczane.ad", read_only=True)
    olusturan_adi = serializers.SerializerMethodField()
    talep_turu_ad = serializers.CharField(source="talep_turu.ad", read_only=True)
    talep_turu_kod = serializers.CharField(source="talep_turu.kod", read_only=True)
    alan_ad = serializers.CharField(source="alan.ad", read_only=True)
    alan_kod = serializers.CharField(source="alan.kod", read_only=True)
    alt_konu_ad = serializers.CharField(source="alt_konu.ad", read_only=True)
    alt_konu_kod = serializers.CharField(source="alt_konu.kod", read_only=True)
    durum_ad = serializers.CharField(source="durum.ad", read_only=True)
    durum_kod = serializers.CharField(source="durum.kod", read_only=True)
    kiosk_ad = serializers.SerializerMethodField()

    class Meta:
        model = DestekTalebi
        fields = [
            "id", "talep_no",
            "eczane_adi", "olusturan_adi",
            "talep_turu_ad", "talep_turu_kod",
            "alan_ad", "alan_kod",
            "alt_konu_ad", "alt_konu_kod",
            "durum_ad", "durum_kod",
            "kiosk_ad",
            "olusturulma_tarihi", "son_hareket_tarihi",
        ]

    def get_olusturan_adi(self, obj):
        u = obj.olusturan_kullanici
        if not u:
            return "—"
        return u.get_full_name() or u.username

    def get_kiosk_ad(self, obj):
        return obj.kiosk.ad if obj.kiosk else None


# ── Ticket detail serializer (list + aciklama + yorumlar) ─────────────────────

class DestekTalebiDetailSerializer(DestekTalebiListSerializer):
    yorumlar = DestekYorumuSerializer(many=True, read_only=True)
    eczane_id = serializers.IntegerField(read_only=True)
    kiosk_id = serializers.SerializerMethodField()

    class Meta(DestekTalebiListSerializer.Meta):
        fields = DestekTalebiListSerializer.Meta.fields + [
            "eczane_id", "kiosk_id", "aciklama", "yorumlar",
        ]

    def get_kiosk_id(self, obj):
        return obj.kiosk_id


# ── Ticket create serializer ───────────────────────────────────────────────────

class DestekTalebiCreateSerializer(serializers.Serializer):
    talep_turu_id = serializers.PrimaryKeyRelatedField(
        queryset=DestekParametresi.objects.all()
    )
    alan_id = serializers.PrimaryKeyRelatedField(
        queryset=DestekParametresi.objects.all()
    )
    alt_konu_id = serializers.PrimaryKeyRelatedField(
        queryset=DestekParametresi.objects.all()
    )
    kiosk_id = serializers.PrimaryKeyRelatedField(
        queryset=Kiosk.objects.all(),
        required=False,
        allow_null=True,
    )
    aciklama = serializers.CharField(max_length=1000, allow_blank=False)

    def validate_talep_turu_id(self, value):
        if value.grup != DestekParametresi.Grup.TALEP_TURU:
            raise serializers.ValidationError("Talep türü TALEP_TURU grubundan seçilmelidir.")
        if not value.aktif:
            raise serializers.ValidationError("Seçilen talep türü artık aktif değil.")
        return value

    def validate_alan_id(self, value):
        if value.grup != DestekParametresi.Grup.ALAN:
            raise serializers.ValidationError("Alan ALAN grubundan seçilmelidir.")
        if not value.aktif:
            raise serializers.ValidationError("Seçilen alan artık aktif değil.")
        return value

    def validate_alt_konu_id(self, value):
        if value.grup != DestekParametresi.Grup.ALT_KONU:
            raise serializers.ValidationError("Alt konu ALT_KONU grubundan seçilmelidir.")
        if not value.aktif:
            raise serializers.ValidationError("Seçilen alt konu artık aktif değil.")
        return value

    def validate(self, data):
        alan = data.get("alan_id")
        alt_konu = data.get("alt_konu_id")
        kiosk = data.get("kiosk_id")

        # Alt konunun üst parametresi seçilen alanla eşleşmeli.
        if alan and alt_konu:
            if alt_konu.ust_parametre_id != alan.pk:
                raise serializers.ValidationError(
                    {"alt_konu_id": "Alt konu seçilen alanla eşleşmiyor."}
                )

        user = self.context["request"].user
        eczane = getattr(user, "eczane", None)

        # Portal seçilmişse kiosk boş olmalı.
        if alan and alan.kod == "PORTAL" and kiosk is not None:
            raise serializers.ValidationError(
                {"kiosk_id": "Portal seçiminde ilgili kiosk boş olmalıdır."}
            )

        # Kiosk seçilmişse kullanıcının eczanesine ait olmalı.
        if kiosk and eczane and kiosk.eczane_id != eczane.pk:
            raise serializers.ValidationError(
                {"kiosk_id": "Yalnızca kendi eczanenizin kiosklarını seçebilirsiniz."}
            )

        return data


# ── Admin durum güncelleme serializer ─────────────────────────────────────────

class DestekDurumGuncelleSerializer(serializers.Serializer):
    durum_kod = serializers.CharField(max_length=50)

    def validate_durum_kod(self, value):
        try:
            durum = DestekParametresi.objects.get(
                kod=value, grup=DestekParametresi.Grup.DURUM
            )
        except DestekParametresi.DoesNotExist:
            raise serializers.ValidationError("Geçersiz durum kodu.")
        self._durum = durum
        return value

    def get_durum(self):
        return self._durum
