"""
JSON log formatter — bağımlılıksız, container stdout için yapılandırılmış çıktı.

Ortak alanlar:
  timestamp, level, service, environment, version, event, message,
  logger, correlation_id, exception_type
İsteğe bağlı ek alanlar `extra={...}` ile aktarılır ve otomatik temizlenir.
"""
from __future__ import annotations

import json
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any

from .correlation import get_correlation_id
from .redaction import DEFAULT_SENSITIVE_KEYS, REDACTED, sanitize

_RESERVED_LOGRECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "asctime", "message", "taskName",
}

# Handled exception'ların iki farklı logger tarafından tekrar yazılmaması için
# request middleware'den ve exception handler'dan işaretleyebiliriz.
LOG_HANDLED_MARK = "_eisa_exception_logged"


class JsonFormatter(logging.Formatter):
    """
    Yapılandırılmış JSON log formatter.

    Constructor kwargs:
      service_name   — servisin adı (LOG_ekstra alanları üzerine yazılabilir).
      environment    — çalışma ortamı.
      version        — build/image sürümü.
    """

    def __init__(
        self,
        *,
        service_name: str = "unknown",
        environment: str = "unknown",
        version: str = "unknown",
    ) -> None:
        super().__init__()
        self._service = service_name
        self._environment = environment
        self._version = version

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover - triggered via logging
        payload: dict[str, Any] = {
            "timestamp": _format_timestamp(record.created),
            "level": record.levelname,
            "service": getattr(record, "service", self._service),
            "environment": getattr(record, "environment", self._environment),
            "version": getattr(record, "version", self._version),
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = getattr(record, "correlation_id", None) or get_correlation_id()
        if correlation_id:
            payload["correlation_id"] = correlation_id

        event = getattr(record, "event", None)
        if event:
            payload["event"] = str(event)

        # Exception bilgisi — sanitize edilerek eklenir.
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            payload["exception_type"] = getattr(exc_type, "__name__", "Exception") if exc_type else "Exception"
            stack = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            if len(stack) > 8192:
                stack = stack[:8192] + f"…[+{len(stack) - 8192}c]"
            payload["stack"] = stack
        elif record.exc_text:
            payload["stack"] = str(record.exc_text)[:8192]

        # Ek alanlar (extra={...}) — hassas veriler burada temizlenir.
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOGRECORD_ATTRS or key.startswith("_"):
                continue
            if key in payload:
                continue
            if key.lower() in DEFAULT_SENSITIVE_KEYS:
                payload[key] = REDACTED
                continue
            payload[key] = sanitize(value)

        try:
            return json.dumps(payload, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            fallback = {
                "timestamp": payload.get("timestamp"),
                "level": payload.get("level"),
                "service": payload.get("service"),
                "environment": payload.get("environment"),
                "version": payload.get("version"),
                "logger": payload.get("logger"),
                "message": "log_serialize_failed",
                "original_logger": record.name,
            }
            return json.dumps(fallback, ensure_ascii=False)


def _format_timestamp(created: float) -> str:
    dt = datetime.fromtimestamp(created, tz=timezone.utc)
    # RFC3339 / ISO-8601 with millisecond precision and trailing Z.
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(dt.microsecond / 1000):03d}Z"


def resolve_default_service() -> str:
    """Container ortam değişkeninden servis adını çözer."""
    return os.getenv("SERVICE_NAME", "eisa-backend")
