"""
Eczane ve kiosk serileştiricileri — admin panel CRUD için.
"""
from rest_framework import serializers

from .models import Kiosk, Pharmacy


class PharmacySerializer(serializers.ModelSerializer):
    """Eczane oluşturma, güncelleme ve listeleme için serileştirici."""

    class Meta:
        model = Pharmacy
        fields = ["id", "name", "city", "district", "address", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class KioskSerializer(serializers.ModelSerializer):
    """
    Kiosk serileştiricisi.
    app_key: sadece okunur — oluşturma/yenileme işlemleri server tarafında yapılır.
    last_seen_at: sadece okunur — KioskAppKeyAuthentication tarafından güncellenir.
    """

    class Meta:
        model = Kiosk
        fields = [
            "id",
            "pharmacy",
            "mac_address",
            "app_key",
            "is_active",
            "last_seen_at",
            "created_at",
        ]
        read_only_fields = ["id", "app_key", "last_seen_at", "created_at"]
