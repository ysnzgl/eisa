"""Kullanici serileştiricisi."""
from rest_framework import serializers

from .models import Kullanici


class KullaniciSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kullanici
        fields = ["id", "username", "email", "rol", "eczane"]
        read_only_fields = ["id", "username", "rol"]
