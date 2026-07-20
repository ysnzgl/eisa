"""kiosk_api facade — provisioning + operasyonel endpoint + auth testleri.

Kesin kararlar (bkz. gorev):
  - Operasyonel endpoint'ler TEK auth: Authorization: AppKey <key> + X-Kiosk-MAC.
  - Bootstrap App Key doner (iot_token URETILMEZ).
  - 401: App Key/MAC eksik veya App Key/MAC cifti gecersiz.
  - 403: kiosk pasif / onaysiz / eczaneye bagli degil.
"""
import hashlib
import hmac as _hmac
import uuid
from datetime import datetime, timedelta, timezone as _tz

import pytest

from apps.analytics.models import OturumLogu
from apps.lookups.models import Cinsiyet, YasAraligi
from apps.pharmacies.models import Kiosk, KioskProvisioningRequest
from apps.products.models import Kategori

FLEET_KEY = "kiosk-api-fleet-key"
PROVISION_SECRET = "kiosk-api-provision-secret"
BOOTSTRAP_URL = "/api/kiosk/v1/bootstrap/"
NEW_MAC = "AA:11:BB:22:CC:33"

OPERATIONAL_GET = [
    "/api/kiosk/v1/ping/",
    "/api/kiosk/v1/sync/",
    "/api/kiosk/v1/catalog/",
    "/api/kiosk/v1/playlist/",
]


@pytest.fixture(autouse=True)
def _kiosk_settings(settings):
    settings.KIOSK_FLEET_KEY = FLEET_KEY
    settings.KIOSK_PROVISIONING_SECRET = PROVISION_SECRET


def _ts(offset_sec: int = 0) -> str:
    return (datetime.now(_tz.utc) + timedelta(seconds=offset_sec)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sign(mac: str, ts: str, secret: str = PROVISION_SECRET) -> str:
    return _hmac.new(secret.encode(), (mac.upper() + ts).encode(), hashlib.sha256).hexdigest()


def _bootstrap_body(mac: str, secret: str = PROVISION_SECRET, ts: str | None = None) -> dict:
    ts = ts or _ts()
    return {"mac_adresi": mac, "timestamp": ts, "hmac": _sign(mac, ts, secret)}


def _appkey_creds(client, kiosk: Kiosk):
    client.credentials(
        HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
        HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
    )
    return client


# ── Bootstrap / Provisioning ─────────────────────────────────────────────────

class TestBootstrap:
    def test_unknown_device_pending_no_app_key(self, db, api_client):
        r = api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json",
                            HTTP_X_KIOSK_KEY=FLEET_KEY)
        assert r.status_code == 202, r.content
        data = r.json()
        assert data["status"] == "PENDING"
        assert "registration_id" in data
        assert "retry_after_seconds" in data
        assert "app_key" not in data
        assert not Kiosk.objects.filter(mac_adresi__iexact=NEW_MAC).exists()

    def test_duplicate_pending_single_record(self, db, api_client):
        api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        assert KioskProvisioningRequest.objects.filter(mac_adresi__iexact=NEW_MAC).count() == 1

    def test_invalid_fleet_key_401(self, db, api_client):
        r = api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json",
                            HTTP_X_KIOSK_KEY="wrong")
        assert r.status_code == 401
        assert not KioskProvisioningRequest.objects.filter(mac_adresi__iexact=NEW_MAC).exists()

    def test_invalid_hmac_401(self, db, api_client):
        ts = _ts()
        body = {"mac_adresi": NEW_MAC, "timestamp": ts, "hmac": "de" * 32}
        r = api_client.post(BOOTSTRAP_URL, body, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        assert r.status_code == 401

    def test_stale_timestamp_400(self, db, api_client):
        old = _ts(offset_sec=-4000)
        body = {"mac_adresi": NEW_MAC, "timestamp": old, "hmac": _sign(NEW_MAC, old)}
        r = api_client.post(BOOTSTRAP_URL, body, format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        assert r.status_code == 400

    def test_approved_device_gets_app_key(self, db, api_client, admin_client, eczane):
        api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=NEW_MAC)
        admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/",
            {"eczane_id": eczane.id, "ad": "Kiosk A"}, format="json",
        )
        r = api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        assert r.status_code == 200, r.content
        data = r.json()
        assert data["status"] == "APPROVED"
        assert data["kiosk_id"] and data["pharmacy_id"]
        assert data["app_key"]
        assert "iot_token" not in data
        # SQLite tarafinda saklanacak degerin backend'deki App Key ile ayni olmasi
        kiosk = Kiosk.objects.get(mac_adresi__iexact=NEW_MAC)
        assert data["app_key"] == kiosk.uygulama_anahtari

    def test_repeat_bootstrap_same_app_key(self, db, api_client, admin_client, eczane):
        api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=NEW_MAC)
        admin_client.post(
            f"/api/pharmacies/kiosks/provisioning/{req.id}/approve/",
            {"eczane_id": eczane.id, "ad": "Kiosk A"}, format="json",
        )
        r1 = api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        r2 = api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        assert r1.json()["app_key"] == r2.json()["app_key"]

    def test_rejected_device_403_no_app_key(self, db, api_client, admin_client):
        api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        req = KioskProvisioningRequest.objects.get(mac_adresi__iexact=NEW_MAC)
        admin_client.post(f"/api/pharmacies/kiosks/provisioning/{req.id}/reject/", {}, format="json")
        r = api_client.post(BOOTSTRAP_URL, _bootstrap_body(NEW_MAC), format="json", HTTP_X_KIOSK_KEY=FLEET_KEY)
        assert r.status_code == 403
        assert r.json()["status"] == "REJECTED"
        assert "app_key" not in r.json()


# ── Operasyonel endpoint auth ────────────────────────────────────────────────

class TestOperationalAuth:
    @pytest.mark.parametrize("url", OPERATIONAL_GET)
    def test_valid_app_key_ok(self, db, api_client, kiosk, url):
        _appkey_creds(api_client, kiosk)
        assert api_client.get(url).status_code == 200

    @pytest.mark.parametrize("url", OPERATIONAL_GET)
    def test_missing_app_key_401(self, db, api_client, url):
        assert api_client.get(url).status_code == 401

    def test_invalid_app_key_401(self, db, api_client, kiosk):
        api_client.credentials(HTTP_AUTHORIZATION="AppKey wrong-key",
                               HTTP_X_KIOSK_MAC=kiosk.mac_adresi)
        assert api_client.get("/api/kiosk/v1/ping/").status_code == 401

    def test_missing_mac_401(self, db, api_client, kiosk):
        api_client.credentials(HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}")
        assert api_client.get("/api/kiosk/v1/ping/").status_code == 401

    def test_wrong_mac_401(self, db, api_client, kiosk):
        # Gecerli App Key + baska bir MAC => MAC/App Key cifti gecersiz => 401
        api_client.credentials(HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
                               HTTP_X_KIOSK_MAC="99:99:99:99:99:99")
        assert api_client.get("/api/kiosk/v1/ping/").status_code == 401

    def test_bearer_token_rejected(self, db, api_client, kiosk):
        api_client.credentials(HTTP_AUTHORIZATION="Bearer some.jwt.token")
        assert api_client.get("/api/kiosk/v1/ping/").status_code == 401

    def test_fleet_key_alone_rejected(self, db, api_client):
        api_client.credentials(HTTP_X_KIOSK_KEY=FLEET_KEY)
        assert api_client.get("/api/kiosk/v1/ping/").status_code == 401

    def test_jwt_panel_user_rejected(self, db, admin_client):
        # admin_client Bearer JWT tasir; kiosk endpoint'i JWT kabul etmez.
        assert admin_client.get("/api/kiosk/v1/ping/").status_code == 401

    def test_inactive_kiosk_403(self, db, api_client, eczane):
        passive = Kiosk.objects.create(
            eczane=eczane, ad="Pasif", mac_adresi="DE:AD:BE:EF:00:09",
            uygulama_anahtari="passive-key-secure-48chars-xxxxxxxxxxxxxxxxxx",
            aktif=False,
        )
        _appkey_creds(api_client, passive)
        assert api_client.get("/api/kiosk/v1/ping/").status_code == 403


# ── Operasyonel endpoint davranisi ───────────────────────────────────────────

class TestOperationalBehaviour:
    def test_sync_shape(self, db, api_client, kiosk):
        _appkey_creds(api_client, kiosk)
        body = api_client.get("/api/kiosk/v1/sync/").json()
        assert body["kiosk_id"] == kiosk.pk
        assert "creatives" in body and "house_ads" in body and "lookups" in body

    def test_catalog_shape(self, db, api_client, kiosk):
        _appkey_creds(api_client, kiosk)
        body = api_client.get("/api/kiosk/v1/catalog/").json()
        assert "kategoriler" in body and "etken_maddeler" in body and "danisma_kategorileri" in body

    def test_ping_shape(self, db, api_client, kiosk):
        _appkey_creds(api_client, kiosk)
        body = api_client.get("/api/kiosk/v1/ping/").json()
        assert body["kiosk_id"] == kiosk.pk
        assert "playlist_version" in body

    def test_sessions_ingest(self, db, api_client, kiosk):
        Kategori.objects.create(ad="Uyku", slug="uyku")
        yas = YasAraligi.objects.first()
        cins = Cinsiyet.objects.first()
        _appkey_creds(api_client, kiosk)
        payload = {"items": [{
            "idempotency_anahtari": str(uuid.uuid4()),
            "yas_araligi_kod": yas.kod,
            "cinsiyet_kod": cins.kod,
            "kategori_slug": "uyku",
            "qr_kodu": "A1B2C3D4",
            "cevaplar": {},
            "onerilen_etken_maddeler": [],
            "tamamlandi": True,
        }]}
        r = api_client.post("/api/kiosk/v1/sessions/", payload, format="json")
        assert r.status_code == 200, r.content
        assert r.json()["accepted"] == 1
        # Oturum, payload'a degil dogrulanmis kiosk'a baglanir
        assert OturumLogu.objects.filter(kiosk=kiosk, qr_kodu="A1B2C3D4").exists()

    def test_diagnostics_ingest(self, db, api_client, kiosk):
        _appkey_creds(api_client, kiosk)
        payload = {"items": [{"level": "WARNING", "event": "test_event", "message": "hi"}]}
        r = api_client.post("/api/kiosk/v1/diagnostics/", payload, format="json")
        assert r.status_code == 202, r.content
        assert r.json()["accepted"] == 1
