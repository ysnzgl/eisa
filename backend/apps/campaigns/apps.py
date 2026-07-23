from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.campaigns"

    def ready(self) -> None:
        # Sinyalleri kaydet (Campaign + Creative + DeliveryRule + CampaignTarget + HouseAd + Kiosk)
        import apps.campaigns.signals  # noqa: F401
