"""Kullanici serileştiricileri."""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.pharmacies.models import Eczane

from .models import Kullanici


class KullaniciSerializer(serializers.ModelSerializer):
    """Profil endpoint'i için (kendi profili)."""

    class Meta:
        model = Kullanici
        fields = ["id", "username", "email", "rol", "eczane"]
        read_only_fields = ["id", "username", "rol"]


class EczaneMinSerializer(serializers.ModelSerializer):
    class Meta:
        model = Eczane
        fields = ["id", "ad"]


class KullaniciAdminSerializer(serializers.ModelSerializer):
    """Admin kullanıcı yönetim listesi/detayı."""

    eczane_detail = EczaneMinSerializer(source="eczane", read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Kullanici
        fields = [
            "id", "username", "email", "first_name", "last_name", "full_name",
            "rol", "eczane", "eczane_detail",
            "is_active", "date_joined", "last_login",
        ]
        read_only_fields = ["id", "username", "date_joined", "last_login", "full_name", "eczane_detail"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class KullaniciCreateSerializer(serializers.ModelSerializer):
    """Yeni kullanıcı oluşturma."""

    password = serializers.CharField(write_only=True, required=True, min_length=6)

    class Meta:
        model = Kullanici
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "rol", "eczane", "password", "is_active",
        ]
        read_only_fields = ["id"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Kullanici(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(required=True, min_length=6)

    def validate_password(self, value):
        validate_password(value)
        return value
