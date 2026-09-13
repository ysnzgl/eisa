"""İş takip serializer'ları."""
from django.db import transaction
from rest_framework import serializers

from apps.core.uow import UnitOfWork
from apps.users.models import Kullanici

from .models import Gorev


class GorevSerializer(serializers.ModelSerializer):
    durum_ad = serializers.CharField(source="get_durum_display", read_only=True)
    atanan_kullanici_adi = serializers.SerializerMethodField()
    atanan_kullanici_username = serializers.SerializerMethodField()
    olusturan_adi = serializers.SerializerMethodField()
    atanan_kullanici_id = serializers.PrimaryKeyRelatedField(
        source="atanan_kullanici",
        queryset=Kullanici.objects.filter(rol=Kullanici.Rol.SUPERADMIN, is_active=True),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Gorev
        fields = [
            "id",
            "baslik",
            "icerik",
            "durum",
            "durum_ad",
            "atanan_kullanici_id",
            "atanan_kullanici_adi",
            "atanan_kullanici_username",
            "olusturan_adi",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
        ]
        read_only_fields = [
            "id",
            "durum_ad",
            "atanan_kullanici_adi",
            "atanan_kullanici_username",
            "olusturan_adi",
            "olusturulma_tarihi",
            "guncellenme_tarihi",
        ]

    def get_atanan_kullanici_adi(self, obj):
        user = obj.atanan_kullanici
        if not user:
            return None
        return user.get_full_name() or user.username

    def get_atanan_kullanici_username(self, obj):
        return obj.atanan_kullanici.username if obj.atanan_kullanici else None

    def get_olusturan_adi(self, obj):
        user = obj.olusturan
        if not user:
            return "—"
        return user.get_full_name() or user.username

    def create(self, validated_data):
        instance = Gorev(**validated_data)
        with transaction.atomic():
            with UnitOfWork(user=self.context["request"].user) as uow:
                uow.add(instance)
        return instance

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        with transaction.atomic():
            with UnitOfWork(user=self.context["request"].user) as uow:
                uow.update(instance)
        return instance
