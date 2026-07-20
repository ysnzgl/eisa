"""
Kiosk Provision Onay Akisi — Backend Testleri.

Kapsam:
  - Gecerli kimlik + bilinmeyen cihaz → PENDING (202)
  - Gecersiz fleet key → 401, kayit yok
  - Gecersiz HMAC → 401, kayit yok
  - Ayni cihazin tekrar basvurmasi → duplicate yok, request_count artar
  - Admin olmayan kullanici → 403
  - SuperAdmin cihazi eczaneye baglar → Kiosk olusur, APPROVED
  - Onay sonrasi cihaz bootstrap → 200 iot_token
  - Reddedilen cihaz bootstrap → 403 REJECTED
  - Ayni cihaz iki kez onay → ikinci kiosk olusmuyor
  - Secret redaction → log/response icinde hassas deger yok
  - Mevcut kayitli kiosk → eski akis bozulmuyor
"""
import hashlib
import hmac as _hmac
from datetime import datetime, timezone as _tz

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.lookups.models import Il, Ilce
from apps.lookups.seed import seed_lookups
from apps.pharmacies.models import Eczane, Kiosk, KioskProvisioningRequest


# ── Yardimcilar ───────────────────────────────────────────────────────────────

FLEET_KEY = "test-fleet-key-xxx"
PROVISION_SECRET = "test-provision-secret-yyy"
BOOTSTRAP_URL = "/api/kiosk/v1/bootstrap/"
PROVISIONING_LIST_URL = "/api/pharmacies/kiosks/provisioning/"
UNKNOWN_MAC = "AA:BB:CC:DD:EE:FF"
REGISTERED_MAC = "11:22:33:44:55:66"


def _hmac_sign(mac: str, timestamp: str, secret: str) -> str:
    message = mac.upper() + timestamp
    return _hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _fresh_timestamp() -> str:
    return datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bootstrap_payload(mac: str, secret: str = PROVISION_SECRET) -> dict:
    ts = _fresh_timestamp()
    return {
        "mac_adresi": mac,
        "timestamp": ts,
        "hmac": _hmac_sign(mac, ts, secret),
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
    Kullanici = get_user_model()
    return Kullanici.objects.create_user(
        username="superadmin_prov",
        password="Str0ngPass!",
        rol="superadmin",
    )


@pytest.fixture
def non_admin(db):
    from django.contrib.auth import get_user_model
    Kullanici = get_user_model()
    return Kullanici.objects.create_user(
        username="eczaci_prov",
        password="Str0ngPass!",
        rol="pharmacist",
    )


@pytest.fixture
def eczane(db):
    seed_lookups()
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Kadikoy")
    return Eczane.objects.create(ad="Test Eczanesi Prov", il=il, ilce=ilce)


@pytest.fixture
def registered_kiosk(db, eczane):
    return Kiosk.objects.create(
        eczane=eczane,
        ad="Kayitli Kiosk",
        mac_adresi=REGISTERED_MAC,
        uygulama_anahtari="registered-app-key-secure-48chars-xxxxxxxxxxxxxxxxx",
        aktif=True,
    )


@pytest.fixture
def admin_client(api_client, superadmin):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(superadmin)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def non_admin_client(api_client, non_admin):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(non_admin)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


# ── 1. Gecerli kimlik + bilinmeyen cihaz → PENDING ────────────────────────────

class TestBootstrapUnknownDevice:
    def test_creates_pending_record_returns_202(self, db, api_client):
        """Geçerli fleet key + HMAC + bilinmeyen MAC → 202 PENDING, kiosk oluşmaz."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        response = api_client.post(
            BOOTSTRAP_URL,
            payload,
            format="json",
            HTTP_X_KIOSK_KEY=FLEET_KEY,
        )
        assert response.status_code == 202, response.data
        data = response.json()
        assert data["status"] == "PENDING"
        assert "registration_id" in data
        assert "retry_after_seconds" in data

        # Kiosk oluşmamış olmalı
        assert not Kiosk.objects.filter(mac_adresi__iexact=UNKNOWN_MAC).exists()
        # Pending kayıt var
        req = KioskProvisioningRequest.objects.filter(mac_adresi__iexact=UNKNOWN_MAC).first()
        assert req is not None
        assert req.status == KioskProvisioningRequest.Status.PENDING
        assert req.request_count == 1

    def test_response_contains_no_secrets(self, db, api_client):
        """Response içinde fleet key veya provision secret bulunmamalı."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        response = api_client.post(
            BOOTSTRAP_URL,
            payload,
            format="json",
            HTTP_X_KIOSK_KEY=FLEET_KEY,
        )
        response_text = response.content.decode()
        assert FLEET_KEY not in response_text
        assert PROVISION_SECRET not in response_text


# ── 2. Gecersiz fleet key ──────────────────────────────────────────────────────

class TestBootstrapInvalidFleetKey:
    def test_invalid_fleet_key_401_no_record(self, db, api_client):
        """Geçersiz fleet key → 401, pending kayıt oluşmaz."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        response = api_client.post(
            BOOTSTRAP_URL,
            payload,
            format="json",
            HTTP_X_KIOSK_KEY="yanlis-fleet-key",
        )
        assert response.status_code == 401
        assert not KioskProvisioningRequest.objects.filter(mac_adresi__iexact=UNKNOWN_MAC).exists()

    def test_missing_fleet_key_header_401(self, db, api_client):
        """Fleet key header eksik → 401."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        response = api_client.post(BOOTSTRAP_URL, payload, format="json")
        assert response.status_code == 401

    def test_error_message_does_not_reveal_which_credential_failed(self, db, api_client):
        """Hata mesajı hangi credential'ın hatalı olduğunu belirtmemeli."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        response = api_client.post(
            BOOTSTRAP_URL,
            payload,
            format="json",
            HTTP_X_KIOSK_KEY="yanlis-fleet-key",
        )
        # "fleet" veya "key" gibi spesifik bilgi içermemeli
        detail = response.json().get("detail", "")
        assert "fleet" not in detail.lower()
        assert FLEET_KEY not in detail


# ── 3. Gecersiz HMAC ──────────────────────────────────────────────────────────

class TestBootstrapInvalidHmac:
    def test_invalid_hmac_401_no_record(self, db, api_client):
        """Geçersiz HMAC → 401, pending kayıt oluşmaz."""
        ts = _fresh_timestamp()
        payload = {
            "mac_adresi": UNKNOWN_MAC,
            "timestamp": ts,
            "hmac": "aa" * 32,  # hatalı imza
        }
        response = api_client.post(
            BOOTSTRAP_URL,
            payload,
            format="json",
            HTTP_X_KIOSK_KEY=FLEET_KEY,
        )
        assert response.status_code == 401
        assert not KioskProvisioningRequest.objects.filter(mac_adresi__iexact=UNKNOWN_MAC).exists()


# ── 4. Ayni cihazin tekrar basvurmasi ────────────────────────────────────────

class TestBootstrapIdempotency:
    def test_same_device_no_duplicate_pending(self, db, api_client):
        """Aynı cihaz tekrar başvurduğunda yeni pending kayıt oluşmaz."""
        payload1 = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload1, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        payload2 = _bootstrap_payload(UNKNOWN_MAC)
        response2 = api_client.post(
            BOOTSTRAP_URL, payload2, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY
        )
        assert response2.status_code == 202

        count = KioskProvisioningRequest.objects.filter(mac_adresi__iexact=UNKNOWN_MAC).count()
        assert count == 1

    def test_request_count_increments(self, db, api_client):
        """Tekrar başvuruda request_count artmalı."""
        for _ in range(3):
            payload = _bootstrap_payload(UNKNOWN_MAC)
            api_client.post(BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=UNKNOWN_MAC)
        assert req.request_count == 3

    def test_last_seen_at_updated(self, db, api_client):
        """Tekrar başvuruda last_seen_at güncellenmelidir."""
        payload1 = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload1, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        req_before = KioskProvisioningRequest.objects.get(mac_adresi__iexact=UNKNOWN_MAC)
        t1 = req_before.last_seen_at

        payload2 = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload2, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        req_after = KioskProvisioningRequest.objects.get(mac_adresi__iexact=UNKNOWN_MAC)
        t2 = req_after.last_seen_at
        assert t2 >= t1

    def test_registration_id_same_across_retries(self, db, api_client):
        """Aynı cihaz için dönen registration_id sabit kalmalı."""
        payload1 = _bootstrap_payload(UNKNOWN_MAC)
        r1 = api_client.post(BOOTSTRAP_URL, payload1, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        payload2 = _bootstrap_payload(UNKNOWN_MAC)
        r2 = api_client.post(BOOTSTRAP_URL, payload2, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        assert r1.json()["registration_id"] == r2.json()["registration_id"]


# ── 5. Admin olmayan kullanici ────────────────────────────────────────────────

class TestProvisioningAdminAccess:
    def test_non_admin_cannot_list_provisioning(self, db, non_admin_client):
        """Admin olmayan kullanıcı provisioning listesine erişemez."""
        response = non_admin_client.get(PROVISIONING_LIST_URL)
        assert response.status_code == 403

    def test_anonymous_cannot_list_provisioning(self, db, api_client):
        """Anonim kullanıcı provisioning listesine erişemez."""
        response = api_client.get(PROVISIONING_LIST_URL)
        assert response.status_code in (401, 403)

    def test_non_admin_cannot_approve(self, db, non_admin_client):
        """Admin olmayan kullanıcı onaylama yapamaz."""
        req = KioskProvisioningRequest.objects.create(
            mac_adresi="DE:AD:BE:EF:00:01",
            status=KioskProvisioningRequest.Status.PENDING,
        )
        response = non_admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/",
            {"eczane_id": 1, "ad": "Test"},
            format="json",
        )
        assert response.status_code == 403

    def test_non_admin_cannot_reject(self, db, non_admin_client):
        """Admin olmayan kullanıcı reddetme yapamaz."""
        req = KioskProvisioningRequest.objects.create(
            mac_adresi="DE:AD:BE:EF:00:02",
            status=KioskProvisioningRequest.Status.PENDING,
        )
        response = non_admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/reject/",
            {"rejection_reason": ""},
            format="json",
        )
        assert response.status_code == 403


# ── 6. SuperAdmin onay akisi ──────────────────────────────────────────────────

class TestAdminApproval:
    def test_approve_creates_kiosk_approved_record(self, db, admin_client, eczane, api_client):
        """SuperAdmin cihazı onayladığında Kiosk oluşur ve pending → approved."""
        # Önce bootstrap ile pending oluştur
        payload = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=UNKNOWN_MAC)
        approve_url = f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/"

        response = admin_client.post(
            approve_url,
            {"eczane_id": eczane.id, "ad": "Test Kiosk"},
            format="json",
        )
        assert response.status_code == 200, response.data
        data = response.json()
        assert data["status"] == "APPROVED"
        assert data["kiosk_id"] is not None

        # Kiosk oluştu
        kiosk = Kiosk.objects.filter(mac_adresi__iexact=UNKNOWN_MAC).first()
        assert kiosk is not None
        assert kiosk.eczane_id == eczane.id
        assert kiosk.aktif is True

        # Pending → APPROVED
        req.refresh_from_db()
        assert req.status == KioskProvisioningRequest.Status.APPROVED
        assert req.kiosk == kiosk

    def test_approve_links_correct_pharmacy(self, db, admin_client, eczane, api_client):
        """Onaylanan kiosk doğru eczaneye bağlanmalı."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=UNKNOWN_MAC)
        admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/",
            {"eczane_id": eczane.id, "ad": "Kiosk X"},
            format="json",
        )

        kiosk = Kiosk.objects.get(mac_adresi__iexact=UNKNOWN_MAC)
        assert kiosk.eczane_id == eczane.id


# ── 7. Onay sonrasi cihaz bootstrap ──────────────────────────────────────────

class TestBootstrapAfterApproval:
    def test_approved_device_gets_app_key(self, db, admin_client, eczane, api_client):
        """Onaylanmış cihaz tekrar bootstrap yaptığında App Key alır (iot_token DEĞIL)."""
        # Pending oluştur
        payload = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=UNKNOWN_MAC)

        # Admin onayla
        admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/",
            {"eczane_id": eczane.id, "ad": "Onaylandi Kiosk"},
            format="json",
        )

        # Cihaz tekrar bootstrap
        payload2 = _bootstrap_payload(UNKNOWN_MAC)
        response = api_client.post(
            BOOTSTRAP_URL, payload2, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY
        )
        assert response.status_code == 200, response.data
        data = response.json()
        assert data["status"] == "APPROVED"
        assert data["app_key"]
        assert data["kiosk_id"] is not None
        assert data["pharmacy_id"] is not None
        assert "iot_token" not in data


# ── 8. Reddedilen cihaz ──────────────────────────────────────────────────────

class TestRejectedDevice:
    def test_rejected_device_gets_403(self, db, admin_client, eczane, api_client):
        """Reddedilmiş cihaz bootstrap yaptığında 403 alır."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=UNKNOWN_MAC)
        admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/reject/",
            {"rejection_reason": "Test red"},
            format="json",
        )

        payload2 = _bootstrap_payload(UNKNOWN_MAC)
        response = api_client.post(
            BOOTSTRAP_URL, payload2, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY
        )
        assert response.status_code == 403
        data = response.json()
        assert data["status"] == "REJECTED"

    def test_rejected_device_no_iot_token(self, db, admin_client, api_client):
        """Reddedilmiş cihaz IoT token alamamalı."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=UNKNOWN_MAC)
        admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/reject/",
            {},
            format="json",
        )

        payload2 = _bootstrap_payload(UNKNOWN_MAC)
        response = api_client.post(
            BOOTSTRAP_URL, payload2, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY
        )
        assert "iot_token" not in response.json()


# ── 9. Ayni cihaz iki kez onay → duplicate kiosk yok ─────────────────────────

class TestDuplicateApproval:
    def test_second_approval_no_duplicate_kiosk(self, db, admin_client, eczane, api_client):
        """Aynı cihazın iki kez onaylanması ikinci kiosk oluşturmamalı."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=UNKNOWN_MAC)

        # İlk onay
        admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/",
            {"eczane_id": eczane.id, "ad": "Kiosk 1"},
            format="json",
        )

        # İkinci onay — idempotent olmalı
        response2 = admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/",
            {"eczane_id": eczane.id, "ad": "Kiosk 1"},
            format="json",
        )
        # İkinci çağrı ya 200 (idempotent) ya da 409 (çakışma) döndürmeli
        assert response2.status_code in (200, 409), response2.data

        # Kiosk sayısı 1 olmalı
        kiosk_count = Kiosk.objects.filter(mac_adresi__iexact=UNKNOWN_MAC).count()
        assert kiosk_count == 1


# ── 10. Mevcut kayitli kiosk — eski akis bozulmuyor ──────────────────────────

class TestExistingKioskNotAffected:
    def test_registered_kiosk_still_gets_token(self, db, api_client, registered_kiosk):
        """Önceden kayıtlı kiosk App Key alır; aynı key doner (eski akış bozulmaz)."""
        payload = _bootstrap_payload(REGISTERED_MAC)
        response = api_client.post(
            BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY
        )
        assert response.status_code == 200, response.data
        data = response.json()
        assert data["status"] == "APPROVED"
        assert data["app_key"] == registered_kiosk.uygulama_anahtari

    def test_registered_kiosk_no_pending_created(self, db, api_client, registered_kiosk):
        """Kayıtlı kiosk için pending kayıt oluşmamalı."""
        payload = _bootstrap_payload(REGISTERED_MAC)
        api_client.post(BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        assert not KioskProvisioningRequest.objects.filter(
            mac_adresi__iexact=REGISTERED_MAC
        ).exists()


# ── 11. Serializer'da hassas alan sikintisi yok ────────────────────────────────

class TestSerializerSecrets:
    def test_provisioning_list_no_secret_fields(self, db, admin_client, api_client):
        """Admin provisioning list response'unda fleet_key veya secret bulunmamalı."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)

        response = admin_client.get(PROVISIONING_LIST_URL)
        assert response.status_code == 200
        response_text = response.content.decode()
        assert FLEET_KEY not in response_text
        assert PROVISION_SECRET not in response_text
        assert "hmac" not in response_text.lower()

    def test_provisioning_response_no_iot_token(self, db, admin_client, eczane, api_client):
        """Onay response'unda iot_token verilmemeli (cihaz kendi bootstrap eder)."""
        payload = _bootstrap_payload(UNKNOWN_MAC)
        api_client.post(BOOTSTRAP_URL, payload, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=UNKNOWN_MAC)

        response = admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/",
            {"eczane_id": eczane.id, "ad": "Kiosk Sec"},
            format="json",
        )
        assert "iot_token" not in response.json()
