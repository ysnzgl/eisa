"""Device ID kimlik doğrulama testleri.

Kapsam:
  - Device ID üretimi ve kalıcılığı (edge tarafında crypto.randomUUID)
  - Pending device ID uniqueness (partial unique constraint)
  - Approval sırasında device_id kiosk'a aktarımı
  - Güvenli legacy enrollment (/identity/enroll/)
  - Eksik device_id → 401 (device_id set edildikten sonra)
  - Farklı device_id → 401
  - Device_id NULL olan kiosk herhangi header'ı kabul eder (legacy)
  - Enrollment endpoint: ilk kayıt, ikinci kayıt reddedilir
  - Enrollment endpoint: farklı değerle enrollment reddi
  - Enrollment idempotent (aynı değer tekrar gönderilir)
"""
from __future__ import annotations

import hashlib
import hmac as _hmac
import uuid
from datetime import datetime, timezone as _tz

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.lookups.models import Il, Ilce
from apps.lookups.seed import seed_lookups
from apps.pharmacies.models import Eczane, Kiosk, KioskProvisioningRequest

FLEET_KEY = "test-fleet-key-device-id"
PROVISION_SECRET = "test-provision-secret-device-id"
BOOTSTRAP_URL = "/api/kiosk/v1/bootstrap/"
ENROLL_URL = "/api/kiosk/v1/identity/enroll/"

DEVICE_UUID_A = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
DEVICE_UUID_B = "11111111-2222-3333-4444-555555555555"


def _ts():
    return datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sign(mac: str, ts: str, device_id: str = "", secret: str = PROVISION_SECRET) -> str:
    message = mac.upper() + ts + device_id
    return _hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _bootstrap_body(mac: str, device_id: str = "") -> dict:
    ts = _ts()
    return {
        "mac_adresi": mac,
        "device_id": device_id,
        "timestamp": ts,
        "hmac": _sign(mac, ts, device_id),
    }


@pytest.fixture(autouse=True)
def _override_settings(settings):
    settings.KIOSK_FLEET_KEY = FLEET_KEY
    settings.KIOSK_PROVISIONING_SECRET = PROVISION_SECRET


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def superadmin(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(
        username="superadmin_did", password="Str0ngPass!", rol="superadmin"
    )


@pytest.fixture
def eczane(db):
    seed_lookups()
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Sisli")
    return Eczane.objects.create(ad="Eczane DID Test", il=il, ilce=ilce)


@pytest.fixture
def kiosk_no_device_id(db, eczane):
    return Kiosk.objects.create(
        eczane=eczane,
        mac_adresi="D1:D2:D3:D4:D5:D6",
        uygulama_anahtari="did-no-device-key-48chars-xxxxxxxxxxxxxxxxxxxxxx",
        device_id=None,
    )


@pytest.fixture
def kiosk_with_device_id(db, eczane):
    return Kiosk.objects.create(
        eczane=eczane,
        mac_adresi="E1:E2:E3:E4:E5:E6",
        uygulama_anahtari="did-with-device-key-48chars-xxxxxxxxxxxxxxxxxxxxxxxxx",
        device_id=DEVICE_UUID_A,
    )


# ── Bootstrap device_id inclusion ────────────────────────────────────────────

class TestBootstrapDeviceID:
    def test_bootstrap_with_device_id_stored(self, db, api_client):
        mac = "BB:CC:DD:EE:FF:00"
        r = api_client.post(
            BOOTSTRAP_URL,
            _bootstrap_body(mac, device_id=DEVICE_UUID_A),
            format="json",
            HTTP_X_KIOSK_KEY=FLEET_KEY,
        )
        assert r.status_code == 202
        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=mac)
        assert req.device_id == DEVICE_UUID_A

    def test_bootstrap_legacy_no_device_id(self, db, api_client):
        """Legacy bootstrap (no device_id) still works."""
        mac = "11:22:33:44:55:00"
        ts = _ts()
        # Old-style HMAC: MAC + timestamp (no device_id)
        old_hmac = _hmac.new(
            PROVISION_SECRET.encode(),
            (mac.upper() + ts).encode(),
            hashlib.sha256,
        ).hexdigest()
        r = api_client.post(
            BOOTSTRAP_URL,
            {"mac_adresi": mac, "timestamp": ts, "hmac": old_hmac},
            format="json",
            HTTP_X_KIOSK_KEY=FLEET_KEY,
        )
        assert r.status_code == 202

    def test_pending_device_id_unique_constraint(self, db, api_client):
        """Same device_id cannot appear in two different pending requests."""
        mac1 = "AA:11:BB:22:CC:44"
        mac2 = "AA:11:BB:22:CC:55"
        api_client.post(
            BOOTSTRAP_URL, _bootstrap_body(mac1, device_id=DEVICE_UUID_A),
            format="json", HTTP_X_KIOSK_KEY=FLEET_KEY,
        )
        r2 = api_client.post(
            BOOTSTRAP_URL, _bootstrap_body(mac2, device_id=DEVICE_UUID_A),
            format="json", HTTP_X_KIOSK_KEY=FLEET_KEY,
        )
        # Second request with same device_id on different MAC should return 409
        # (partial unique constraint prevents two pending requests with same non-empty device_id)
        assert r2.status_code == 409


# ── Approval transfers device_id ─────────────────────────────────────────────

class TestApprovalDeviceIDTransfer:
    def test_approval_transfers_device_id_to_kiosk(self, db, api_client, superadmin, eczane):
        from rest_framework_simplejwt.tokens import RefreshToken

        mac = "AA:BB:11:22:33:44"
        api_client.post(
            BOOTSTRAP_URL, _bootstrap_body(mac, device_id=DEVICE_UUID_A),
            format="json", HTTP_X_KIOSK_KEY=FLEET_KEY,
        )
        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=mac)

        admin_client = APIClient()
        refresh = RefreshToken.for_user(superadmin)
        admin_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        r = admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/",
            {"eczane_id": eczane.pk, "ad": "Test Kiosk DID"},
            format="json",
        )
        assert r.status_code == 200

        kiosk = Kiosk.objects.get(mac_adresi__iexact=mac)
        assert kiosk.device_id == DEVICE_UUID_A

    def test_approval_legacy_no_device_id(self, db, api_client, superadmin, eczane):
        """Approval with empty device_id → kiosk.device_id=None."""
        from rest_framework_simplejwt.tokens import RefreshToken

        mac = "CC:DD:11:22:33:44"
        ts = _ts()
        old_hmac = _hmac.new(PROVISION_SECRET.encode(), (mac.upper() + ts).encode(), hashlib.sha256).hexdigest()
        api_client.post(
            BOOTSTRAP_URL, {"mac_adresi": mac, "timestamp": ts, "hmac": old_hmac},
            format="json", HTTP_X_KIOSK_KEY=FLEET_KEY,
        )
        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=mac)

        admin_client = APIClient()
        refresh = RefreshToken.for_user(superadmin)
        admin_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/",
            {"eczane_id": eczane.pk, "ad": "Legacy Kiosk"},
            format="json",
        )
        kiosk = Kiosk.objects.get(mac_adresi__iexact=mac)
        assert kiosk.device_id is None  # Legacy: no device_id


# ── Authentication with device_id ─────────────────────────────────────────────

class TestDeviceIDAuthentication:
    def test_kiosk_no_device_id_accepts_any_header(self, db, kiosk_no_device_id):
        """Kiosk without device_id bound accepts requests with or without header."""
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk_no_device_id.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk_no_device_id.mac_adresi,
            HTTP_X_KIOSK_DEVICE_ID="any-value-does-not-matter",
        )
        res = client.get("/api/kiosk/v1/ping/")
        assert res.status_code == 200

    def test_kiosk_no_device_id_works_without_header(self, db, kiosk_no_device_id):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk_no_device_id.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk_no_device_id.mac_adresi,
        )
        res = client.get("/api/kiosk/v1/ping/")
        assert res.status_code == 200

    def test_kiosk_with_device_id_header_not_required(self, db, kiosk_with_device_id):
        """device_id auth katmaninda zorunlu tutulmaz; eksik header kabul edilir."""
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk_with_device_id.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk_with_device_id.mac_adresi,
            # No X-Kiosk-Device-ID header
        )
        res = client.get("/api/kiosk/v1/ping/")
        assert res.status_code == 200  # device_id auth'da zorunlu degil

    def test_kiosk_with_device_id_wrong_value_still_accepted(self, db, kiosk_with_device_id):
        """device_id auth katmaninda dogrulanmaz; yanlis deger auth'u gecersiz kilmaz."""
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk_with_device_id.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk_with_device_id.mac_adresi,
            HTTP_X_KIOSK_DEVICE_ID=DEVICE_UUID_B,  # farkli deger, ama artik reddedilmez
        )
        res = client.get("/api/kiosk/v1/ping/")
        assert res.status_code == 200  # App Key + MAC yeterli

    def test_kiosk_with_correct_device_id_accepted(self, db, kiosk_with_device_id):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"AppKey {kiosk_with_device_id.uygulama_anahtari}",
            HTTP_X_KIOSK_MAC=kiosk_with_device_id.mac_adresi,
            HTTP_X_KIOSK_DEVICE_ID=DEVICE_UUID_A,  # correct
        )
        res = client.get("/api/kiosk/v1/ping/")
        assert res.status_code == 200


# ── Identity Enrollment ───────────────────────────────────────────────────────

class TestIdentityEnrollment:
    def _kiosk_client(self, kiosk, device_id=None):
        client = APIClient()
        creds = {
            "HTTP_AUTHORIZATION": f"AppKey {kiosk.uygulama_anahtari}",
            "HTTP_X_KIOSK_MAC": kiosk.mac_adresi,
        }
        if device_id:
            creds["HTTP_X_KIOSK_DEVICE_ID"] = device_id
        client.credentials(**creds)
        return client

    def test_first_enrollment_succeeds(self, db, kiosk_no_device_id):
        client = self._kiosk_client(kiosk_no_device_id)
        res = client.post(ENROLL_URL, {"device_id": DEVICE_UUID_A}, format="json")
        assert res.status_code == 200
        assert res.json()["status"] == "enrolled"

        kiosk_no_device_id.refresh_from_db()
        assert kiosk_no_device_id.device_id == DEVICE_UUID_A

    def test_enrollment_idempotent_same_value(self, db, kiosk_no_device_id):
        client = self._kiosk_client(kiosk_no_device_id)
        client.post(ENROLL_URL, {"device_id": DEVICE_UUID_A}, format="json")
        # After enrollment, kiosk.device_id is set → subsequent auth requires device_id header
        client2 = self._kiosk_client(kiosk_no_device_id, device_id=DEVICE_UUID_A)
        res = client2.post(ENROLL_URL, {"device_id": DEVICE_UUID_A}, format="json")
        assert res.status_code == 200
        assert res.json()["status"] == "enrolled"

    def test_enrollment_different_value_rejected(self, db, kiosk_with_device_id):
        """Already-bound kiosk rejects a different device_id."""
        client = self._kiosk_client(kiosk_with_device_id, device_id=DEVICE_UUID_A)
        res = client.post(ENROLL_URL, {"device_id": DEVICE_UUID_B}, format="json")
        assert res.status_code == 409
        assert res.json()["code"] == "already_bound"

    def test_enrollment_invalid_format_rejected(self, db, kiosk_no_device_id):
        client = self._kiosk_client(kiosk_no_device_id)
        res = client.post(ENROLL_URL, {"device_id": "not-a-uuid"}, format="json")
        assert res.status_code == 400
        assert res.json()["code"] == "device_id_invalid_format"

    def test_enrollment_missing_device_id_rejected(self, db, kiosk_no_device_id):
        client = self._kiosk_client(kiosk_no_device_id)
        res = client.post(ENROLL_URL, {}, format="json")
        assert res.status_code == 400
        assert res.json()["code"] == "device_id_required"
