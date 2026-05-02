"""Eczane ve Kiosk cihaz modelleri."""
from django.db import models


class Pharmacy(models.Model):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=64)
    district = models.CharField(max_length=64)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pharmacies"
        verbose_name_plural = "Pharmacies"

    def __str__(self) -> str:
        return self.name


class Kiosk(models.Model):
    """Eczanedeki fiziksel kiosk cihaz. App-Key + MAC eşleşmesiyle yetkilenir."""

    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name="kiosks")
    mac_address = models.CharField(max_length=17, unique=True)
    app_key = models.CharField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "kiosks"
