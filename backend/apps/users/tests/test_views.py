"""User görünüm testleri — GET/PATCH /api/users/me/."""
import pytest


@pytest.mark.django_db
class TestProfileView:
    url = "/api/users/me/"

    def test_unauthenticated_returns_401(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == 401

    def test_superadmin_can_get_own_profile(self, admin_client, superadmin):
        resp = admin_client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "superadmin"
        assert data["role"] == "superadmin"

    def test_pharmacist_can_get_own_profile(self, pharmacist_client, pharmacist):
        resp = pharmacist_client.get(self.url)
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "pharmacist"
        assert data["role"] == "pharmacist"

    def test_profile_read_only_fields_not_writable(self, admin_client, superadmin):
        resp = admin_client.patch(self.url, {"username": "hacker", "role": "superadmin"})
        assert resp.status_code == 200
        # Kullanıcı adı ve rol değişmemeli
        superadmin.refresh_from_db()
        assert superadmin.username == "superadmin"
        assert superadmin.role == "superadmin"

    def test_patch_email(self, admin_client, superadmin):
        resp = admin_client.patch(self.url, {"email": "new@example.com"})
        assert resp.status_code == 200
        superadmin.refresh_from_db()
        assert superadmin.email == "new@example.com"

    def test_put_not_allowed(self, admin_client):
        resp = admin_client.put(self.url, {"email": "a@b.com"})
        assert resp.status_code == 405
