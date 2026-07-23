"""
Campaigns test paketi için conftest.

Campaign post_save signal'larını autouse fixture ile devre dışı bırakır.
Neden: Signal handler arka planda thread başlatır; SQLite test DB'si transaction
içinde kilitli olduğundan thread "database table is locked" hatası alır.
"""
import pytest
from django.db.models.signals import post_save

from apps.campaigns.models import Campaign
from apps.campaigns.signals import _on_campaign_save


@pytest.fixture(autouse=True)
def disable_campaign_signals():
    """Campaign post_save sinyalini test süresince devre dışı bırak."""
    post_save.disconnect(_on_campaign_save, sender=Campaign)
    yield
    post_save.connect(_on_campaign_save, sender=Campaign)
