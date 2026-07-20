"""
Log ingestion görünümleri (teknik loglar için).

İki uç sunar:
    * `POST /api/kiosk/v1/diagnostics/` — kiosk cihazlarından batch olarak
    gelen diagnostic outbox kayıtlarını normalize edip standart JSON logu olarak
    stdout'a yazar. Kayıtlar PostgreSQL'e YAZILMAZ; iş verisi değildir.
  * `POST /api/analytics/client-events/` — web panelinden gelen kritik client
    hatalarını sanitize edip JSON logu olarak stdout'a yazar.

Politika:
  - Payload boyutu, batch büyüklüğü ve alan boyutları sıkıca sınırlanır.
  - Rate limit uygulanır.
  - Alan listesi allow-list olarak zorlanır.
  - Hassas veriler sanitize edilir (bkz. apps.core.logging.redaction).
"""
from __future__ import annotations

import logging
from typing import Any, Iterable

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.logging.correlation import get_correlation_id
from apps.core.logging.redaction import sanitize
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

# Kiosk diagnostic outbox event kayıtları için ayrı bir logger; formatter ortak
# JSON formatter'ı kullanır ve zaten stdout'a yazar.
kiosk_diag_logger = logging.getLogger("eisa.kiosk.diagnostic")
client_event_logger = logging.getLogger("eisa.client")


ALLOWED_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
_ALLOWED_LEVEL_SET = {lvl.upper() for lvl in ALLOWED_LEVELS}

MAX_BATCH_ITEMS = 100
MAX_MESSAGE_LEN = 4096
MAX_STACK_LEN = 8192
MAX_EVENT_LEN = 128
MAX_CONTEXT_KEYS = 32

# Kiosk diagnostic gövdesinde izin verilen alanlar (allow-list).
KIOSK_ALLOWED_FIELDS = {
    "level",
    "event",
    "message",
    "context",
    "correlation_id",
    "occurred_at",
}

# Client event gövdesinde izin verilen alanlar (allow-list).
CLIENT_ALLOWED_FIELDS = {
    "level",
    "event",
    "message",
    "stack",
    "component",
    "route",
    "user_agent_brand",
    "correlation_id",
    "occurred_at",
}


def _normalize_level(raw: Any) -> str:
    if isinstance(raw, str):
        candidate = raw.upper()
        if candidate in _ALLOWED_LEVEL_SET:
            return candidate
    return "INFO"


def _truncate(value: Any, limit: int) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    if len(text) > limit:
        return text[:limit] + f"…[+{len(text) - limit}c]"
    return text


def _pick_allowed(item: dict[str, Any], allowed: Iterable[str]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key in allowed}


def ingest_kiosk_diagnostic_items(kiosk, items: list[Any]) -> dict[str, Any]:
    """Kiosk diagnostic outbox kayitlarini sanitize edip JSON stdout log'a yazar.

    DB'ye YAZILMAZ; is verisi degildir. `items` cagirandan once dogrulanmis
    (liste + boyut siniri) olmalidir. Doner: {accepted, rejected, errors,
    accepted_keys}.
    """
    kiosk_id = getattr(kiosk, "pk", None)
    pharmacy_id = getattr(kiosk, "eczane_id", None)

    accepted_keys: list[str] = []
    errors: list[dict[str, Any]] = []
    base_correlation = get_correlation_id()

    for index, raw in enumerate(items):
        if not isinstance(raw, dict):
            errors.append({"index": index, "error": "item_not_object"})
            continue
        filtered = _pick_allowed(raw, KIOSK_ALLOWED_FIELDS)
        level = _normalize_level(filtered.get("level"))
        event = _truncate(filtered.get("event") or "kiosk_diagnostic", MAX_EVENT_LEN)
        message = _truncate(filtered.get("message") or event, MAX_MESSAGE_LEN)
        context = filtered.get("context") if isinstance(filtered.get("context"), dict) else {}
        if len(context) > MAX_CONTEXT_KEYS:
            context = dict(list(context.items())[:MAX_CONTEXT_KEYS])
        context = sanitize(context)
        correlation_id = filtered.get("correlation_id") or base_correlation

        extra = {
            "event": event,
            "kiosk_id": kiosk_id,
            "pharmacy_id": pharmacy_id,
            "source": "kiosk_diagnostic",
            "context": context,
        }
        if correlation_id and isinstance(correlation_id, str):
            extra["correlation_id"] = correlation_id[:64]
        occurred_at = filtered.get("occurred_at")
        if isinstance(occurred_at, str) and len(occurred_at) <= 64:
            extra["occurred_at"] = occurred_at

        kiosk_diag_logger.log(_level_number(level), message, extra=extra)

        key = raw.get("id") or raw.get("correlation_id")
        if isinstance(key, (str, int)):
            accepted_keys.append(str(key))

    return {
        "accepted": len(items) - len(errors),
        "rejected": len(errors),
        "errors": errors,
        "accepted_keys": accepted_keys,
    }


class ClientEventIngestView(APIView):
    """Web panelinden gelen kritik frontend hatalarını normalize eder."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "client_event"

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        items = payload.get("items")
        if items is None and payload:
            items = [payload]
        if not isinstance(items, list) or not items:
            return Response(
                {"detail": "`items` boş olmayan bir liste olmalı."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(items) > MAX_BATCH_ITEMS:
            return Response(
                {"detail": f"Batch en fazla {MAX_BATCH_ITEMS} kayıt içerebilir."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        actor = request.user
        actor_id = getattr(actor, "pk", None)
        actor_role = getattr(actor, "rol", None)
        base_correlation = get_correlation_id()

        accepted = 0
        for raw in items:
            if not isinstance(raw, dict):
                continue
            filtered = _pick_allowed(raw, CLIENT_ALLOWED_FIELDS)
            level = _normalize_level(filtered.get("level") or "ERROR")
            event = _truncate(filtered.get("event") or "client_error", MAX_EVENT_LEN)
            message = _truncate(filtered.get("message") or event, MAX_MESSAGE_LEN)
            stack = _truncate(filtered.get("stack"), MAX_STACK_LEN)
            extra = {
                "event": event,
                "source": "web_panel_client",
                "actor_id": actor_id,
                "actor_role": actor_role,
                "component": _truncate(filtered.get("component"), 128),
                "route": _truncate(filtered.get("route"), 256),
                "user_agent_brand": _truncate(filtered.get("user_agent_brand"), 64),
            }
            correlation_id = filtered.get("correlation_id") or base_correlation
            if isinstance(correlation_id, str) and correlation_id:
                extra["correlation_id"] = correlation_id[:64]
            occurred_at = filtered.get("occurred_at")
            if isinstance(occurred_at, str) and len(occurred_at) <= 64:
                extra["occurred_at"] = occurred_at
            if stack:
                extra["stack"] = stack
            client_event_logger.log(_level_number(level), message, extra=extra)
            accepted += 1

        return Response({"accepted": accepted}, status=status.HTTP_202_ACCEPTED)


def _level_number(level: str) -> int:
    mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    return mapping.get(level, logging.INFO)
