"""Anonim demografik ve davranışsal log modelleri (KVKK uyumlu)."""
from django.db import models


class AgeRange(models.TextChoices):
    R_0_17 = "0-17", "0-17"
    R_18_25 = "18-25", "18-25"
    R_26_35 = "26-35", "26-35"
    R_36_50 = "36-50", "36-50"
    R_51_65 = "51-65", "51-65"
    R_65_PLUS = "65+", "65+"


class Gender(models.TextChoices):
    FEMALE = "F", "Kadın"
    MALE = "M", "Erkek"
    OTHER = "O", "Diğer"


class SessionLog(models.Model):
    """Bir kiosk oturumu — kişiyi tanımlamayan tamamen anonim kayıt."""

    kiosk = models.ForeignKey("pharmacies.Kiosk", on_delete=models.CASCADE, related_name="sessions")
    age_range = models.CharField(max_length=8, choices=AgeRange.choices)
    gender = models.CharField(max_length=1, choices=Gender.choices)
    category = models.ForeignKey(
        "products.Category", on_delete=models.PROTECT, related_name="sessions"
    )
    is_sensitive_flow = models.BooleanField(default=False)
    qr_code = models.CharField(max_length=64, db_index=True)
    answers_payload = models.JSONField(default=dict, blank=True)
    suggested_ingredients = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "session_logs"
        indexes = [models.Index(fields=["created_at", "kiosk"])]


class AdImpression(models.Model):
    """DOOH idle moddaki reklam gösterim logu."""

    kiosk = models.ForeignKey("pharmacies.Kiosk", on_delete=models.CASCADE)
    campaign = models.ForeignKey("campaigns.Campaign", on_delete=models.CASCADE)
    shown_at = models.DateTimeField()
    duration_ms = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "ad_impressions"
