"""
Kullanıcı serileştiricileri — JWT ile doğrulanmış panel kullanıcıları için.
"""
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Kullanıcı profili serileştiricisi.
    id, username, role alanları salt okunurdur; email ve pharmacy güncellenebilir.
    """

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "pharmacy"]
        read_only_fields = ["id", "username", "role"]
