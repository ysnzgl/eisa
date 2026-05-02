"""DOOH reklam kampanyaları — lokasyon/yaş/cinsiyet hedefli."""
from django.core.exceptions import ValidationError
from django.db import models


def validate_https_url(value: str) -> None:
    """Yalnızca http(s) şemalarına izin ver — javascript:/file:/data: bloklanır."""
    lower = (value or "").lower()
    if not (lower.startswith("https://") or lower.startswith("http://")):
        raise ValidationError("media_url yalnızca http veya https olabilir.")


class Campaign(models.Model):
    name = models.CharField(max_length=255)
    media_url = models.URLField(validators=[validate_https_url])
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    target_cities = models.JSONField(default=list, blank=True)
    target_districts = models.JSONField(default=list, blank=True)
    target_age_ranges = models.JSONField(default=list, blank=True)
    target_genders = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campaigns"
