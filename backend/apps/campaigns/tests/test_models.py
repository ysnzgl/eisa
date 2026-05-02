"""Campaign model testleri."""
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.campaigns.models import Campaign, validate_https_url


class TestValidateHttpsUrl:
    def test_valid_https_url(self):
        validate_https_url("https://example.com/ad.mp4")  # hata fırlatmamalı

    def test_valid_http_url(self):
        validate_https_url("http://example.com/ad.mp4")

    def test_javascript_url_blocked(self):
        with pytest.raises(ValidationError):
            validate_https_url("javascript:alert(1)")

    def test_file_url_blocked(self):
        with pytest.raises(ValidationError):
            validate_https_url("file:///etc/passwd")

    def test_data_url_blocked(self):
        with pytest.raises(ValidationError):
            validate_https_url("data:text/html,<h1>xss</h1>")

    def test_empty_string_blocked(self):
        with pytest.raises(ValidationError):
            validate_https_url("")


@pytest.mark.django_db
class TestCampaignModel:
    def test_create_campaign(self):
        now = timezone.now()
        c = Campaign.objects.create(
            name="Reklam 1",
            media_url="https://cdn.example.com/video.mp4",
            starts_at=now,
            ends_at=now,
        )
        assert c.is_active is True
        assert c.target_cities == []
        assert c.target_genders == []

    def test_db_table_name(self):
        assert Campaign._meta.db_table == "campaigns"
