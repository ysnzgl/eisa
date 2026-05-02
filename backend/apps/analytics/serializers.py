"""
Analitik serileştiricileri.
Kiosk outbox veri iletimi ve admin panel görünümleri için.
"""
from rest_framework import serializers

from .models import AdImpression, AgeRange, Gender, SessionLog


class SessionLogItemSerializer(serializers.Serializer):
    """
    Kiosk'tan gelen tek bir oturum kaydı için giriş serileştiricisi.
    kiosk_mac: doğrulama için kabul edilir ancak kimlik doğrulamasından gelen kiosk kullanılır.
    created_at: kiosk'un orijinal zaman damgası; auto_now_add'ı aşmak için kullanılır.
    """

    kiosk_mac = serializers.CharField(max_length=17, required=False, allow_blank=True)
    age_range = serializers.ChoiceField(choices=AgeRange.choices)
    gender = serializers.ChoiceField(choices=Gender.choices)
    category_slug = serializers.SlugField()
    is_sensitive_flow = serializers.BooleanField(default=False)
    qr_code = serializers.CharField(max_length=64)
    answers_payload = serializers.JSONField(default=dict)
    suggested_ingredients = serializers.JSONField(default=list)
    # Kiosk'un orijinal zaman damgası (zorunlu değil; verilmezse server zamanı kullanılır)
    created_at = serializers.DateTimeField(required=False, allow_null=True)


class AdImpressionItemSerializer(serializers.Serializer):
    """Kiosk'tan gelen tek bir reklam gösterim kaydı için giriş serileştiricisi."""

    campaign_id = serializers.IntegerField()
    shown_at = serializers.DateTimeField()
    duration_ms = serializers.IntegerField(min_value=0, default=0)


class SessionLogSerializer(serializers.ModelSerializer):
    """Admin panel için oturum kaydı listeleme serileştiricisi."""

    # İlişkili model alanlarını düzleştirerek doğrudan erişim sağla
    category_name = serializers.CharField(source="category.name", read_only=True)
    kiosk_mac = serializers.CharField(source="kiosk.mac_address", read_only=True)
    pharmacy_name = serializers.CharField(source="kiosk.pharmacy.name", read_only=True)

    class Meta:
        model = SessionLog
        fields = [
            "id",
            "kiosk",
            "kiosk_mac",
            "pharmacy_name",
            "age_range",
            "gender",
            "category",
            "category_name",
            "is_sensitive_flow",
            "qr_code",
            "answers_payload",
            "suggested_ingredients",
            "created_at",
        ]
