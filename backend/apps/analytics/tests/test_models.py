"""Analytics model testleri."""
import pytest
from django.utils import timezone

from apps.analytics.models import SessionLog, AdImpression
from apps.products.models import Category
from apps.campaigns.models import Campaign


@pytest.fixture
def category(db):
    return Category.objects.create(name="Enerji", slug="enerji")


@pytest.fixture
def session_log(db, kiosk, category):
    return SessionLog.objects.create(
        kiosk=kiosk,
        age_range="26-35",
        gender="M",
        category=category,
        qr_code="QR123456",
    )


@pytest.fixture
def campaign(db):
    now = timezone.now()
    return Campaign.objects.create(
        name="Test Kampanya",
        media_url="https://example.com/ad.mp4",
        starts_at=now,
        ends_at=now,
    )


@pytest.mark.django_db
class TestSessionLogModel:
    def test_create_session_log(self, session_log):
        assert session_log.id is not None
        assert session_log.is_sensitive_flow is False
        assert session_log.answers_payload == {}
        assert session_log.suggested_ingredients == []

    def test_db_table_name(self):
        assert SessionLog._meta.db_table == "session_logs"

    def test_qr_code_indexed(self):
        field = SessionLog._meta.get_field("qr_code")
        assert field.db_index is True


@pytest.mark.django_db
class TestAdImpressionModel:
    def test_create_impression(self, kiosk, campaign):
        impression = AdImpression.objects.create(
            kiosk=kiosk,
            campaign=campaign,
            shown_at=timezone.now(),
            duration_ms=5000,
        )
        assert impression.duration_ms == 5000

    def test_db_table_name(self):
        assert AdImpression._meta.db_table == "ad_impressions"
