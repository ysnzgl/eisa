"""Kiosk API facade app config."""
from django.apps import AppConfig


class KioskApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.kiosk_api"
    verbose_name = "Kiosk API (facade)"
