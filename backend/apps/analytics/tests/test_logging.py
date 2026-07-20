"""Merkezi loglama altyapisi testleri.

Kontroller:
  - Yapisal JSON formatter beklenen alanlari uretir ve sanitize eder.
  - Korelasyon ID middleware'i UUID uretir, mevcutsa kabul eder ve response'a yazar.
  - `sanitize` fonksiyonu hassas alanlari maskeler.
  - Diagnostic + client-event ingestion endpoint'leri sadece izin verilen
    payload'i normalize edip stdout'a JSON log olarak yazar (DB'ye YAZMAZ).
"""
from __future__ import annotations

import json
import logging
import uuid

import pytest
from django.urls import reverse

from apps.core.logging.correlation import (
    CORRELATION_HEADER,
    get_correlation_id,
    new_correlation_id,
    sanitize_incoming,
    set_correlation_id,
)
from apps.core.logging.formatters import JsonFormatter
from apps.core.logging.redaction import DEFAULT_SENSITIVE_KEYS, REDACTED, sanitize


def _make_record(msg="hello", *, level=logging.INFO, name="eisa.tests", extra=None):
    record = logging.LogRecord(
        name=name, level=level, pathname=__file__, lineno=10,
        msg=msg, args=(), exc_info=None,
    )
    if extra:
        for key, value in extra.items():
            setattr(record, key, value)
    return record


class TestJsonFormatter:
    def test_produces_valid_json_with_required_fields(self):
        formatter = JsonFormatter(service_name="svc", environment="test", version="9.9.9")
        record = _make_record(msg="ping")
        payload = json.loads(formatter.format(record))

        for key in ("timestamp", "level", "service", "environment", "version", "logger", "message"):
            assert key in payload
        assert payload["service"] == "svc"
        assert payload["environment"] == "test"
        assert payload["version"] == "9.9.9"
        assert payload["message"] == "ping"
        assert payload["timestamp"].endswith("Z")

    def test_includes_correlation_id_from_context(self):
        formatter = JsonFormatter(service_name="svc", environment="test", version="1")
        cid = new_correlation_id()
        set_correlation_id(cid)
        try:
            payload = json.loads(formatter.format(_make_record()))
        finally:
            set_correlation_id(None)
        assert payload["correlation_id"] == cid

    def test_sanitizes_extra_fields(self):
        formatter = JsonFormatter(service_name="svc", environment="test", version="1")
        record = _make_record(
            extra={
                "event": "user_login",
                "authorization": "Bearer supersecret",
                "context": {"token": "abc", "email": "a@b.com", "safe": "ok"},
            }
        )
        payload = json.loads(formatter.format(record))
        assert payload["event"] == "user_login"
        assert payload["authorization"] == REDACTED
        assert payload["context"]["token"] == REDACTED
        assert payload["context"]["email"] == REDACTED
        assert payload["context"]["safe"] == "ok"

    def test_records_exception_details(self):
        formatter = JsonFormatter(service_name="svc", environment="test", version="1")
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="eisa", level=logging.ERROR, pathname=__file__, lineno=10,
            msg="fail", args=(), exc_info=exc_info,
        )
        payload = json.loads(formatter.format(record))
        assert payload["exception_type"] == "ValueError"
        assert "boom" in payload["stack"]


class TestSanitize:
    @pytest.mark.parametrize("key", sorted(DEFAULT_SENSITIVE_KEYS))
    def test_masks_default_sensitive_keys(self, key):
        result = sanitize({key: "value"})
        assert result[key] == REDACTED

    def test_case_insensitive(self):
        assert sanitize({"AUTHORIZATION": "x"})["AUTHORIZATION"] == REDACTED
        assert sanitize({"CoOkIe": "x"})["CoOkIe"] == REDACTED

    def test_recursive(self):
        payload = {"outer": {"password": "p", "safe": [1, 2, {"token": "t"}]}}
        clean = sanitize(payload)
        assert clean["outer"]["password"] == REDACTED
        assert clean["outer"]["safe"][2]["token"] == REDACTED

    def test_truncates_long_strings(self):
        long_value = "x" * 4000
        clean = sanitize({"note": long_value})
        assert clean["note"].startswith("x")
        assert clean["note"] != long_value  # truncated

    def test_unserializable_becomes_repr(self):
        class Weird:
            def __repr__(self):
                return "Weird()"
        clean = sanitize({"x": Weird()})
        assert clean["x"] == "Weird()"


class TestCorrelationHelpers:
    def test_new_id_is_hex(self):
        cid = new_correlation_id()
        assert len(cid) == 32
        assert all(c in "0123456789abcdef" for c in cid)

    @pytest.mark.parametrize("value", [None, "", "  ", "x" * 300, "bad;value", "a b"])
    def test_sanitize_rejects_unsafe(self, value):
        assert sanitize_incoming(value) is None

    def test_sanitize_accepts_uuid(self):
        cid = uuid.uuid4().hex
        assert sanitize_incoming(cid) == cid


@pytest.mark.django_db
class TestCorrelationMiddleware:
    def test_generates_id_when_missing(self, api_client):
        response = api_client.get("/api/lookups/cinsiyetler/")
        assert response.status_code in (200, 401, 403)  # endpoint mevcut
        cid = response.headers.get(CORRELATION_HEADER)
        assert cid, "correlation id header'i eksik"
        assert sanitize_incoming(cid) == cid

    def test_preserves_incoming_id(self, api_client):
        provided = uuid.uuid4().hex
        response = api_client.get(
            "/api/lookups/cinsiyetler/",
            HTTP_X_CORRELATION_ID=provided,
        )
        assert response.headers.get(CORRELATION_HEADER) == provided


@pytest.mark.django_db
class TestClientEventIngest:
    def test_requires_authentication(self, api_client):
        r = api_client.post("/api/analytics/client-events/", {}, format="json")
        assert r.status_code in (401, 403)

    def test_accepts_and_sanitizes(self, admin_client):
        # caplog `propagate: False` yapilmis loggerlari yakalayamiyor;
        # bu yuzden logger'a dogrudan MemoryHandler baglayarak dogruluyoruz.
        captured = []

        class _Capture(logging.Handler):
            def emit(self, record):
                captured.append(record)

        target = logging.getLogger("eisa.client")
        handler = _Capture(level=logging.DEBUG)
        target.addHandler(handler)
        try:
            r = admin_client.post(
                "/api/analytics/client-events/",
                {
                    "items": [
                        {
                            "level": "ERROR",
                            "event": "vue_error_handler",
                            "message": "Cannot read of undefined",
                            "stack": "at Component()",
                            "component": "CampaignWizard",
                            "route": "/admin/campaigns?token=SECRET",
                            "password": "should-not-be-here",
                        }
                    ]
                },
                format="json",
            )
        finally:
            target.removeHandler(handler)
        assert r.status_code == 202
        assert r.data["accepted"] == 1
        assert any(getattr(rec, "event", None) == "vue_error_handler" for rec in captured)
        # password sadece allow-list alaninda olmadigi icin ekstra alan olarak da yazilmamali.
        for rec in captured:
            assert not hasattr(rec, "password"), "hassas alan lograkaydina eklenmemeli"

    def test_batch_limit(self, admin_client):
        payload = {"items": [{"event": "test"} for _ in range(200)]}
        r = admin_client.post("/api/analytics/client-events/", payload, format="json")
        assert r.status_code == 413


@pytest.fixture
def istanbul_kiosk(db):
    """Kiosk fixture'u — Il seed'e bagli olmadan olusturulur."""
    from apps.lookups.models import Il, Ilce
    from apps.pharmacies.models import Eczane, Kiosk
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Kadikoy")
    eczane = Eczane.objects.create(ad="Test Eczanesi", il=il, ilce=ilce)
    return Kiosk.objects.create(
        eczane=eczane,
        mac_adresi="AA:BB:CC:DD:EE:11",
        uygulama_anahtari="test-diag-key-secure-48chars-xxxxxxxxxxxxxxxxxx",
    )


@pytest.fixture
def istanbul_kiosk_client(api_client, istanbul_kiosk):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"AppKey {istanbul_kiosk.uygulama_anahtari}",
        HTTP_X_KIOSK_MAC=istanbul_kiosk.mac_adresi,
    )
    return api_client


@pytest.mark.django_db
class TestKioskDiagnosticIngest:
    def test_requires_kiosk_auth(self, api_client):
        r = api_client.post("/api/kiosk/v1/diagnostics/", {}, format="json")
        assert r.status_code in (401, 403)

    def test_accepts_batch(self, istanbul_kiosk_client):
        captured = []

        class _Capture(logging.Handler):
            def emit(self, record):
                captured.append(record)

        target = logging.getLogger("eisa.kiosk.diagnostic")
        handler = _Capture(level=logging.DEBUG)
        target.addHandler(handler)
        try:
            r = istanbul_kiosk_client.post(
                "/api/kiosk/v1/diagnostics/",
                {
                    "items": [
                        {
                            "id": 1,
                            "level": "ERROR",
                            "event": "sync_sessions_failed",
                            "message": "backend 503",
                            "context": {"attempt": 3, "token": "SECRET"},
                        },
                        {
                            "id": 2,
                            "level": "WARNING",
                            "event": "media_playback_failed",
                            "message": "codec unsupported",
                        },
                    ]
                },
                format="json",
            )
        finally:
            target.removeHandler(handler)
        assert r.status_code == 202
        assert r.data["accepted"] == 2
        assert "1" in r.data["accepted_keys"]
        # `context.token` sanitize edilmis olmali.
        for rec in captured:
            ctx = getattr(rec, "context", {})
            if isinstance(ctx, dict) and "token" in ctx:
                assert ctx["token"] == "***"

    def test_batch_limit(self, istanbul_kiosk_client):
        payload = {"items": [{"level": "ERROR", "event": "e"} for _ in range(200)]}
        r = istanbul_kiosk_client.post("/api/kiosk/v1/diagnostics/", payload, format="json")
        assert r.status_code == 413
