"""
PostgreSQL integration testleri için conftest.

Campaign post_save signal'larını disable eder (playlist regeneration background task).
"""
import pytest
from django.db.models.signals import post_save
from apps.campaigns.models import Campaign


@pytest.fixture(scope="function", autouse=True)
def disable_campaign_signals():
    """
    Campaign post_save signal'ını devre dışı bırak.
    
    Playlist regeneration background task thread'lerde DB bağlantısı açar.
    Bu bağlantılar test teardown'da sorun yaratır.
    """
    # Signal handler'ı bul
    from apps.campaigns.signals import _on_campaign_save
    
    # Disconnect
    post_save.disconnect(_on_campaign_save, sender=Campaign)
    
    yield
    
    # Reconnect (temizlik)
    post_save.connect(_on_campaign_save, sender=Campaign)
