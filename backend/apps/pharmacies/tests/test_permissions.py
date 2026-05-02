"""İzin sınıfı testleri."""
import pytest
from unittest.mock import MagicMock

from apps.pharmacies.permissions import IsSuperAdmin, IsPharmacist, IsKiosk, IsKioskOrAuthenticated


class TestIsSuperAdmin:
    perm = IsSuperAdmin()

    def _request(self, role=None, auth=None):
        r = MagicMock()
        r.user = MagicMock(spec=["role"]) if role else None
        if role:
            r.user.role = role
        r.auth = auth
        return r

    def test_superadmin_allowed(self):
        assert self.perm.has_permission(self._request(role="superadmin"), None) is True

    def test_pharmacist_denied(self):
        assert self.perm.has_permission(self._request(role="pharmacist"), None) is False

    def test_anonymous_denied(self):
        req = MagicMock()
        req.user = None
        assert self.perm.has_permission(req, None) is False


class TestIsPharmacist:
    perm = IsPharmacist()

    def test_pharmacist_allowed(self):
        req = MagicMock()
        req.user = MagicMock(spec=["role"])
        req.user.role = "pharmacist"
        assert self.perm.has_permission(req, None) is True

    def test_superadmin_denied(self):
        req = MagicMock()
        req.user = MagicMock(spec=["role"])
        req.user.role = "superadmin"
        assert self.perm.has_permission(req, None) is False


class TestIsKiosk:
    perm = IsKiosk()

    def test_kiosk_with_string_auth_allowed(self):
        req = MagicMock()
        req.auth = "some-app-key-string"
        assert self.perm.has_permission(req, None) is True

    def test_non_string_auth_denied(self):
        req = MagicMock()
        req.auth = None
        assert self.perm.has_permission(req, None) is False


class TestIsKioskOrAuthenticated:
    perm = IsKioskOrAuthenticated()

    def test_jwt_user_allowed(self):
        req = MagicMock()
        req.user = MagicMock(spec=["role"])
        req.user.role = "pharmacist"
        req.auth = None
        assert self.perm.has_permission(req, None) is True

    def test_kiosk_allowed(self):
        req = MagicMock()
        req.user = MagicMock(spec=[])  # role attribute yok
        req.auth = "app-key"
        assert self.perm.has_permission(req, None) is True

    def test_unauthenticated_denied(self):
        req = MagicMock()
        req.user = None
        req.auth = None
        assert self.perm.has_permission(req, None) is False
