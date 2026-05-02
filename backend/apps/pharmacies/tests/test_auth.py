"""KioskAppKeyAuthentication testleri."""
import pytest
from rest_framework.test import APIRequestFactory

from apps.pharmacies.auth import KioskAppKeyAuthentication
from apps.pharmacies.models import Kiosk


@pytest.mark.django_db
class TestKioskAppKeyAuthentication:
    auth = KioskAppKeyAuthentication()
    factory = APIRequestFactory()

    def _make_request(self, app_key=None, mac=None):
        request = self.factory.get("/")
        if app_key:
            request.META["HTTP_AUTHORIZATION"] = f"AppKey {app_key}"
        if mac:
            request.META["HTTP_X_KIOSK_MAC"] = mac
        return request

    def test_returns_none_without_header(self):
        request = self._make_request()
        result = self.auth.authenticate(request)
        assert result is None

    def test_returns_none_for_bearer_token(self):
        request = self._make_request()
        request.META["HTTP_AUTHORIZATION"] = "Bearer sometoken"
        result = self.auth.authenticate(request)
        assert result is None

    def test_valid_credentials_authenticate(self, kiosk):
        from rest_framework.exceptions import AuthenticationFailed
        request = self._make_request(app_key=kiosk.app_key, mac=kiosk.mac_address)
        result = self.auth.authenticate(request)
        assert result is not None
        authenticated_kiosk, token = result
        assert authenticated_kiosk.id == kiosk.id
        assert token == kiosk.app_key

    def test_wrong_key_raises_error(self, kiosk):
        from rest_framework.exceptions import AuthenticationFailed
        request = self._make_request(app_key="wrong-key", mac=kiosk.mac_address)
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_missing_mac_raises_error(self, kiosk):
        from rest_framework.exceptions import AuthenticationFailed
        request = self._make_request(app_key=kiosk.app_key)
        with pytest.raises(AuthenticationFailed) as exc_info:
            self.auth.authenticate(request)
        assert "MAC" in str(exc_info.value.detail)

    def test_inactive_kiosk_not_authenticated(self, pharmacy):
        from rest_framework.exceptions import AuthenticationFailed
        k = Kiosk.objects.create(
            pharmacy=pharmacy, mac_address="FF:EE:DD:CC:BB:AA", app_key="inactive-key-xxx", is_active=False
        )
        request = self._make_request(app_key="inactive-key-xxx", mac="FF:EE:DD:CC:BB:AA")
        with pytest.raises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_updates_last_seen(self, kiosk):
        assert kiosk.last_seen_at is None
        request = self._make_request(app_key=kiosk.app_key, mac=kiosk.mac_address)
        self.auth.authenticate(request)
        kiosk.refresh_from_db()
        assert kiosk.last_seen_at is not None
