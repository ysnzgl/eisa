"""SessionSubmitRequest ve AdImpressionRequest Pydantic validator testleri."""
import os
os.environ.setdefault("EISA_KIOSK_APP_KEY", "test-app-key-for-testing-only")
os.environ.setdefault("EISA_KIOSK_MAC", "AA:BB:CC:DD:EE:FF")
os.environ.setdefault("EISA_CENTRAL_API_BASE", "http://127.0.0.1:9999")
os.environ.setdefault("EISA_LOCAL_API_SECRET", "test-local-secret")
os.environ.setdefault("EISA_SQLITE_PATH", ":memory:")

import pytest
from pydantic import ValidationError

from kiosk_edge.api.main import SessionSubmitRequest, AdImpressionRequest


class TestSessionSubmitRequest:
    def _valid(self, **kwargs):
        base = {"age_range": "26-35", "gender": "M", "category_slug": "enerji"}
        base.update(kwargs)
        return SessionSubmitRequest(**base)

    def test_valid_request(self):
        req = self._valid()
        assert req.age_range == "26-35"
        assert req.gender == "M"

    @pytest.mark.parametrize("age", ["0-17", "18-25", "26-35", "36-50", "51-65", "65+"])
    def test_all_valid_age_ranges(self, age):
        req = self._valid(age_range=age)
        assert req.age_range == age

    @pytest.mark.parametrize("gender", ["M", "F", "male", "female", "other", "unspecified"])
    def test_all_valid_genders(self, gender):
        req = self._valid(gender=gender)
        assert req.gender == gender

    def test_invalid_age_range(self):
        with pytest.raises(ValidationError) as exc:
            self._valid(age_range="100-999")
        assert "yaş" in str(exc.value).lower() or "age" in str(exc.value).lower()

    def test_invalid_gender(self):
        with pytest.raises(ValidationError):
            self._valid(gender="unknown_gender")

    def test_invalid_qr_code_format(self):
        with pytest.raises(ValidationError):
            self._valid(qr_code="!!!invalid")

    def test_valid_qr_code_format(self):
        req = self._valid(qr_code="QR-ABC123:XYZ")
        assert req.qr_code == "QR-ABC123:XYZ"

    def test_qr_code_can_be_none(self):
        req = self._valid(qr_code=None)
        assert req.qr_code is None

    def test_too_many_ingredients(self):
        with pytest.raises(ValidationError):
            self._valid(suggested_ingredients=[f"ing{i}" for i in range(51)])

    def test_exactly_50_ingredients_ok(self):
        req = self._valid(suggested_ingredients=[f"ing{i}" for i in range(50)])
        assert len(req.suggested_ingredients) == 50

    def test_default_is_sensitive_false(self):
        req = self._valid()
        assert req.is_sensitive_flow is False

    def test_empty_answers_ok(self):
        req = self._valid(answers_payload={})
        assert req.answers_payload == {}


class TestAdImpressionRequest:
    def test_valid_request(self):
        req = AdImpressionRequest(campaign_id=1, shown_at="2026-01-01T12:00:00Z", duration_ms=5000)
        assert req.campaign_id == 1

    def test_zero_campaign_id_rejected(self):
        with pytest.raises(ValidationError):
            AdImpressionRequest(campaign_id=0, shown_at="2026-01-01T12:00:00Z", duration_ms=0)

    def test_negative_duration_rejected(self):
        with pytest.raises(ValidationError):
            AdImpressionRequest(campaign_id=1, shown_at="2026-01-01T12:00:00Z", duration_ms=-1)

    def test_max_duration_ok(self):
        max_ms = 24 * 60 * 60 * 1000
        req = AdImpressionRequest(campaign_id=1, shown_at="2026-01-01T12:00:00Z", duration_ms=max_ms)
        assert req.duration_ms == max_ms

    def test_over_max_duration_rejected(self):
        over_max = 24 * 60 * 60 * 1000 + 1
        with pytest.raises(ValidationError):
            AdImpressionRequest(campaign_id=1, shown_at="2026-01-01T12:00:00Z", duration_ms=over_max)
