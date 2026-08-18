"""
Faz 3+4 backend testleri:
  - PlayLog idempotent proof-of-play (play_event_id)
  - PlayLog status alanı (COMPLETED/FAILED vb.)
  - KioskEvent ingest (idempotency)
  - KioskEventListView (eczane scope)
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.analytics.models import KioskEvent
from apps.campaigns.models import Campaign, Creative, PlayLog
from apps.lookups.seed import seed_lookups
from apps.pharmacies.models import Eczane, Kiosk
from django.contrib.auth import get_user_model

Kullanici = get_user_model()

PROOF_OF_PLAY_URL = "/api/kiosk/v1/proof-of-play/"
KIOSK_EVENTS_URL_INGEST = "/api/kiosk/v1/kiosk-events/"
KIOSK_EVENTS_LIST_URL = "/api/analytics/kiosk-events/"


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _seed(db):
    seed_lookups()


def _make_eczane(ad="Faz3 Eczane"):
    from apps.lookups.models import Il, Ilce
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Kadikoy")
    return Eczane.objects.create(ad=ad, il=il, ilce=ilce)


def _make_kiosk(eczane, mac="F3:F3:F3:F3:F3:F3"):
    return Kiosk.objects.create(
        eczane=eczane, ad="Faz3 Kiosk",
        mac_adresi=mac,
        uygulama_anahtari=f"faz3-key-{mac.replace(':','')}",
    )


def _kiosk_client(kiosk):
    c = APIClient()
    c.credentials(
        HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
        HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
    )
    return c


def _jwt_client(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


def _make_campaign_creative(kiosk):
    camp = Campaign.objects.create(
        name=f"Camp {uuid.uuid4().hex[:6]}",
        start_date=timezone.now() - timedelta(days=1),
        end_date=timezone.now() + timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )
    creative = Creative.objects.create(
        campaign=camp, media_url="https://example.com/ad.mp4", duration_seconds=15,
    )
    return camp, creative


# ─── PlayLog idempotency ──────────────────────────────────────────────────────

class TestProofOfPlayIdempotency:
    def test_same_play_event_id_not_duplicated(self, db):
        eczane = _make_eczane()
        kiosk = _make_kiosk(eczane)
        _, creative = _make_campaign_creative(kiosk)
        client = _kiosk_client(kiosk)

        play_event_id = str(uuid.uuid4())
        payload = {
            "logs": [{
                "creative_id": str(creative.id),
                "played_at": timezone.now().isoformat(),
                "duration_played": 15,
                "play_event_id": play_event_id,
                "status": "COMPLETED",
            }]
        }

        res1 = client.post(PROOF_OF_PLAY_URL, payload, format="json")
        res2 = client.post(PROOF_OF_PLAY_URL, payload, format="json")

        assert res1.status_code == 201
        assert res2.status_code == 201
        assert res2.data["skipped"] == 1
        # Yalnız 1 kayıt oluşmuş olmalı
        assert PlayLog.objects.filter(play_event_id=play_event_id).count() == 1

    def test_without_play_event_id_always_inserts(self, db):
        """Eski kiosk sürümleri (play_event_id=null) her seferinde yeni kayıt oluşturur."""
        eczane = _make_eczane("NoIdEczane")
        kiosk = _make_kiosk(eczane, "A1:A1:A1:A1:A1:A1")
        _, creative = _make_campaign_creative(kiosk)
        client = _kiosk_client(kiosk)

        payload = {
            "logs": [{
                "creative_id": str(creative.id),
                "played_at": timezone.now().isoformat(),
                "duration_played": 10,
            }]
        }
        before = PlayLog.objects.count()
        client.post(PROOF_OF_PLAY_URL, payload, format="json")
        client.post(PROOF_OF_PLAY_URL, payload, format="json")
        assert PlayLog.objects.count() == before + 2  # her seferinde yeni

    def test_status_field_stored(self, db):
        eczane = _make_eczane("StatusEczane")
        kiosk = _make_kiosk(eczane, "B2:B2:B2:B2:B2:B2")
        _, creative = _make_campaign_creative(kiosk)
        client = _kiosk_client(kiosk)

        play_event_id = str(uuid.uuid4())
        payload = {
            "logs": [{
                "creative_id": str(creative.id),
                "played_at": timezone.now().isoformat(),
                "duration_played": 3,
                "play_event_id": play_event_id,
                "status": "FAILED",
                "error_code": "MEDIA_NOT_FOUND",
                "error_summary": "Media file missing",
                "expected_duration": 15,
            }]
        }
        res = client.post(PROOF_OF_PLAY_URL, payload, format="json")
        assert res.status_code == 201

        log = PlayLog.objects.get(play_event_id=play_event_id)
        assert log.status == PlayLog.PlayStatus.FAILED
        assert log.error_code == "MEDIA_NOT_FOUND"
        assert log.expected_duration == 15

    def test_old_kiosk_format_accepted(self, db):
        """Eski kiosk: play_event_id/status olmadan gönderim — backward compat."""
        eczane = _make_eczane("OldKiosk")
        kiosk = _make_kiosk(eczane, "C3:C3:C3:C3:C3:C3")
        _, creative = _make_campaign_creative(kiosk)
        client = _kiosk_client(kiosk)

        payload = {
            "logs": [{
                "creative_id": str(creative.id),
                "played_at": timezone.now().isoformat(),
                "duration_played": 15,
            }]
        }
        res = client.post(PROOF_OF_PLAY_URL, payload, format="json")
        assert res.status_code == 201
        assert res.data["ingested"] == 1
        # Default status = COMPLETED
        log = PlayLog.objects.filter(kiosk=kiosk).last()
        assert log.status == PlayLog.PlayStatus.COMPLETED


# ─── KioskEvent ingest ────────────────────────────────────────────────────────

class TestKioskEventIngest:
    def test_ingest_stores_events(self, db):
        eczane = _make_eczane("EvtIngest")
        kiosk = _make_kiosk(eczane, "D4:D4:D4:D4:D4:D4")
        client = _kiosk_client(kiosk)

        event_id = str(uuid.uuid4())
        payload = {
            "items": [{
                "event_id": event_id,
                "event_type": "SYNC_FAILED",
                "severity": "ERROR",
                "message": "Central API unreachable",
                "occurred_at": timezone.now().isoformat(),
            }]
        }
        res = client.post(KIOSK_EVENTS_URL_INGEST, payload, format="json")
        assert res.status_code == 201
        assert res.data["accepted"] == 1

        evt = KioskEvent.objects.get(event_id=event_id)
        assert evt.event_type == "SYNC_FAILED"
        assert evt.severity == "ERROR"
        assert evt.kiosk == kiosk

    def test_duplicate_event_id_skipped(self, db):
        eczane = _make_eczane("EvtDupe")
        kiosk = _make_kiosk(eczane, "E5:E5:E5:E5:E5:E5")
        client = _kiosk_client(kiosk)

        event_id = str(uuid.uuid4())
        payload = {"items": [{"event_id": event_id, "event_type": "APP_RESTART", "severity": "INFO"}]}

        res1 = client.post(KIOSK_EVENTS_URL_INGEST, payload, format="json")
        res2 = client.post(KIOSK_EVENTS_URL_INGEST, payload, format="json")

        assert res1.status_code == 201
        assert res2.status_code == 201
        assert res2.data["skipped"] == 1
        assert KioskEvent.objects.filter(event_id=event_id).count() == 1

    def test_unknown_event_type_defaults_to_general_error(self, db):
        eczane = _make_eczane("EvtUnknown")
        kiosk = _make_kiosk(eczane, "F6:F6:F6:F6:F6:F6")
        client = _kiosk_client(kiosk)

        event_id = str(uuid.uuid4())
        payload = {"items": [{"event_id": event_id, "event_type": "INVALID_TYPE", "severity": "WARNING"}]}
        res = client.post(KIOSK_EVENTS_URL_INGEST, payload, format="json")
        assert res.status_code == 201
        evt = KioskEvent.objects.get(event_id=event_id)
        assert evt.event_type == "GENERAL_ERROR"

    def test_missing_event_id_skipped(self, db):
        eczane = _make_eczane("EvtNoId")
        kiosk = _make_kiosk(eczane, "G7:G7:G7:G7:G7:G7")
        client = _kiosk_client(kiosk)

        payload = {"items": [{"event_type": "SYNC_FAILED", "severity": "ERROR"}]}
        res = client.post(KIOSK_EVENTS_URL_INGEST, payload, format="json")
        assert res.status_code == 201
        assert res.data["accepted"] == 0

    def test_empty_items_rejected(self, db):
        eczane = _make_eczane("EvtEmpty")
        kiosk = _make_kiosk(eczane, "H8:H8:H8:H8:H8:H8")
        client = _kiosk_client(kiosk)

        res = client.post(KIOSK_EVENTS_URL_INGEST, {"items": []}, format="json")
        assert res.status_code == 400


# ─── KioskEvent list — eczane scope ──────────────────────────────────────────

class TestKioskEventList:
    def _make_event(self, kiosk, event_type="SYNC_FAILED"):
        return KioskEvent.objects.create(
            kiosk=kiosk,
            event_id=uuid.uuid4(),
            event_type=event_type,
            severity="ERROR",
            message="test",
            received_at=timezone.now(),
        )

    def test_eczaci_sees_only_own_events(self, db):
        eczane_a = _make_eczane("EvtListA")
        eczane_b = _make_eczane("EvtListB")
        kiosk_a = _make_kiosk(eczane_a, "I9:I9:I9:I9:I9:I9")
        kiosk_b = _make_kiosk(eczane_b, "J0:J0:J0:J0:J0:J0")

        evt_a = self._make_event(kiosk_a)
        self._make_event(kiosk_b)

        user = Kullanici.objects.create_user(
            username="evt_eczaci", password="X", rol="pharmacist", eczane=eczane_a
        )
        res = _jwt_client(user).get(KIOSK_EVENTS_LIST_URL)
        assert res.status_code == 200
        ids = [r["id"] for r in res.data["results"]]
        assert str(evt_a.id) in ids
        assert len(ids) == 1

    def test_admin_sees_all_events(self, db):
        eczane_a = _make_eczane("EvtAdminA")
        eczane_b = _make_eczane("EvtAdminB")
        kiosk_a = _make_kiosk(eczane_a, "K1:K1:K1:K1:K1:K1")
        kiosk_b = _make_kiosk(eczane_b, "L2:L2:L2:L2:L2:L2")
        self._make_event(kiosk_a)
        self._make_event(kiosk_b)

        admin = Kullanici.objects.create_user(username="evt_admin", password="X", rol="superadmin")
        res = _jwt_client(admin).get(KIOSK_EVENTS_LIST_URL)
        assert res.status_code == 200
        assert res.data["count"] >= 2

    def test_event_type_filter(self, db):
        eczane = _make_eczane("EvtTypeFilter")
        kiosk = _make_kiosk(eczane, "M3:M3:M3:M3:M3:M3")
        self._make_event(kiosk, "SYNC_FAILED")
        self._make_event(kiosk, "APP_RESTART")

        admin = Kullanici.objects.create_user(username="evt_admin2", password="X", rol="superadmin")
        res = _jwt_client(admin).get(KIOSK_EVENTS_LIST_URL, {"event_type": "SYNC_FAILED"})
        assert res.status_code == 200
        types = {r["event_type"] for r in res.data["results"]}
        assert types == {"SYNC_FAILED"}

    def test_eczaci_no_eczane_gets_empty(self, db):
        user = Kullanici.objects.create_user(
            username="evt_noeczane", password="X", rol="pharmacist", eczane=None
        )
        res = _jwt_client(user).get(KIOSK_EVENTS_LIST_URL)
        assert res.status_code == 200
        assert res.data["count"] == 0

    def test_unauthenticated_401(self, db):
        res = APIClient().get(KIOSK_EVENTS_LIST_URL)
        assert res.status_code == 401
