import re

from django.db import transaction
from rest_framework import serializers

from apps.core.uow import UnitOfWork

from .models import BankaHesabi, SirketProfili


def _normalize_iban(value):
    return re.sub(r"\s+", "", (value or "")).upper()


def _iban_is_valid(value):
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}", value):
        return False
    rearranged = value[4:] + value[:4]
    numeric = "".join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)
    return int(numeric) % 97 == 1


class BankaHesabiSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankaHesabi
        fields = (
            "id", "banka_adi", "hesap_sahibi", "iban", "sube_adi", "sube_kodu",
            "hesap_numarasi", "para_birimi", "aciklama", "aktif", "varsayilan", "sira",
            "olusturulma_tarihi", "guncellenme_tarihi", "surum",
        )
        read_only_fields = ("id", "olusturulma_tarihi", "guncellenme_tarihi", "surum")

    def validate_iban(self, value):
        value = _normalize_iban(value)
        if not _iban_is_valid(value):
            raise serializers.ValidationError("Geçerli bir IBAN girin.")
        return value

    def validate(self, attrs):
        aktif = attrs.get("aktif", getattr(self.instance, "aktif", True))
        varsayilan = attrs.get("varsayilan", getattr(self.instance, "varsayilan", False))
        if varsayilan and not aktif:
            raise serializers.ValidationError({"aktif": "Varsayılan banka hesabı aktif olmalıdır."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        sirket = self.context["sirket"]
        instance = BankaHesabi(sirket=sirket, **validated_data)
        with UnitOfWork(user=self.context["request"].user) as uow:
            if validated_data.get("varsayilan"):
                for current in BankaHesabi.objects.filter(sirket=sirket, varsayilan=True):
                    current.varsayilan = False
                    uow.update(current, update_fields=("varsayilan",))
            uow.add(instance)
        return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        with UnitOfWork(user=self.context["request"].user) as uow:
            if validated_data.get("varsayilan"):
                for current in BankaHesabi.objects.filter(
                    sirket=instance.sirket, varsayilan=True
                ).exclude(pk=instance.pk):
                    current.varsayilan = False
                    uow.update(current, update_fields=("varsayilan",))
            for key, value in validated_data.items():
                setattr(instance, key, value)
            uow.update(instance)
        return instance


class SirketProfiliSerializer(serializers.ModelSerializer):
    banka_hesaplari = BankaHesabiSerializer(many=True, read_only=True)

    class Meta:
        model = SirketProfili
        fields = (
            "id", "ticari_unvan", "marka_adi", "vergi_dairesi", "vergi_numarasi",
            "mersis_numarasi", "ticaret_sicil_numarasi", "kep_adresi", "eposta", "telefon",
            "web_sitesi", "adres", "ilce", "il", "posta_kodu", "yetkili_ad_soyad",
            "yetkili_unvan", "banka_hesaplari", "guncellenme_tarihi", "surum",
        )
        read_only_fields = ("id", "banka_hesaplari", "guncellenme_tarihi", "surum")

    def validate_vergi_numarasi(self, value):
        value = re.sub(r"\s+", "", value or "")
        if not re.fullmatch(r"\d{10}", value):
            raise serializers.ValidationError("Vergi numarası 10 rakamdan oluşmalıdır.")
        return value

    def validate_mersis_numarasi(self, value):
        value = re.sub(r"\s+", "", value or "")
        if value and not re.fullmatch(r"\d{16}", value):
            raise serializers.ValidationError("MERSİS numarası 16 rakamdan oluşmalıdır.")
        return value

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        with UnitOfWork(user=self.context["request"].user) as uow:
            uow.update(instance)
        return instance
