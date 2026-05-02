"""PharmacyViewSet ve KioskViewSet endpoint testleri."""
import pytest


@pytest.mark.django_db
class TestPharmacyViewSet:
    list_url = "/api/pharmacies/"

    def test_list_requires_auth(self, api_client):
        resp = api_client.get(self.list_url)
        assert resp.status_code == 401

    def test_superadmin_can_list(self, admin_client, pharmacy):
        resp = admin_client.get(self.list_url)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_pharmacist_can_list(self, pharmacist_client, pharmacy):
        resp = pharmacist_client.get(self.list_url)
        assert resp.status_code == 200

    def test_superadmin_can_create(self, admin_client):
        resp = admin_client.post(self.list_url, {
            "name": "Yeni Eczane", "city": "Ankara", "district": "Çankaya"
        }, format="json")
        assert resp.status_code == 201
        assert resp.json()["name"] == "Yeni Eczane"

    def test_pharmacist_cannot_create(self, pharmacist_client):
        resp = pharmacist_client.post(self.list_url, {
            "name": "Hacker Eczane", "city": "X", "district": "Y"
        }, format="json")
        assert resp.status_code == 403

    def test_superadmin_can_delete(self, admin_client, pharmacy):
        url = f"/api/pharmacies/{pharmacy.id}/"
        resp = admin_client.delete(url)
        assert resp.status_code == 204

    def test_pharmacist_cannot_delete(self, pharmacist_client, pharmacy):
        url = f"/api/pharmacies/{pharmacy.id}/"
        resp = pharmacist_client.delete(url)
        assert resp.status_code == 403


@pytest.mark.django_db
class TestKioskViewSet:
    list_url = "/api/pharmacies/kiosks/"

    def test_superadmin_can_create_kiosk(self, admin_client, pharmacy):
        resp = admin_client.post(self.list_url, {
            "pharmacy": pharmacy.id,
            "mac_address": "11:11:11:11:11:11",
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert "app_key" in data
        assert len(data["app_key"]) > 40  # token_urlsafe(48)

    def test_kiosk_can_access_me_endpoint(self, kiosk_client, kiosk):
        resp = kiosk_client.get("/api/pharmacies/kiosks/me/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mac_address"] == kiosk.mac_address

    def test_non_kiosk_cannot_access_me(self, admin_client):
        resp = admin_client.get("/api/pharmacies/kiosks/me/")
        assert resp.status_code == 403

    def test_regenerate_key(self, admin_client, kiosk):
        old_key = kiosk.app_key
        resp = admin_client.post(f"/api/pharmacies/kiosks/{kiosk.id}/regenerate-key/")
        assert resp.status_code == 200
        new_key = resp.json()["app_key"]
        assert new_key != old_key
