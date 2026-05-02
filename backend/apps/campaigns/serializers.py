"""
Kampanya serileştiricisi — admin CRUD ve kiosk senkronizasyonu için.
"""
from rest_framework import serializers

from .models import Campaign


class CampaignSerializer(serializers.ModelSerializer):
    """
    Kampanya serileştiricisi.
    target_* alanları JSON listelerdir (şehir, ilçe, yaş aralığı, cinsiyet hedefleme).
    """

    class Meta:
        model = Campaign
        fields = [
            "id",
            "name",
            "media_url",
            "starts_at",
            "ends_at",
            "target_cities",
            "target_districts",
            "target_age_ranges",
            "target_genders",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
