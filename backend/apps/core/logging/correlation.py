"""
Korelasyon ID yönetimi.

Bir HTTP isteği veya arka plan işlemi süresince aynı UUID'yi taşıyıp
tüm loglara ve dış çağrılara aktarır. `contextvars` sayesinde iş parçacığı
ve async-güvenli çalışır.
"""
from __future__ import annotations

import re
import uuid
from contextvars import ContextVar
from typing import Optional

CORRELATION_HEADER = "X-Correlation-ID"

# Sunucu içinde geçen ID'nin maksimum uzunluğu; dış girdiyi bu boyla sınırla.
_MAX_LENGTH = 64
# İstek başlığından güvenle kabul edilecek karakterler (base64url + uuid).
_SAFE_RE = re.compile(r"^[A-Za-z0-9._\-]+$")

_current: ContextVar[Optional[str]] = ContextVar("eisa_correlation_id", default=None)


def new_correlation_id() -> str:
    """Yeni bir UUID v4 tabanlı korelasyon ID üretir."""
    return uuid.uuid4().hex


def sanitize_incoming(value: Optional[str]) -> Optional[str]:
    """İstemciden gelen ID'yi normalize edip güvenli değilse None döner."""
    if not value:
        return None
    value = value.strip()
    if not value or len(value) > _MAX_LENGTH:
        return None
    if not _SAFE_RE.match(value):
        return None
    return value


def get_correlation_id() -> Optional[str]:
    """Aktif bağlamdaki korelasyon ID'yi döner (yoksa None)."""
    return _current.get()


def set_correlation_id(value: Optional[str]) -> None:
    """Aktif bağlamın korelasyon ID'sini ayarlar."""
    _current.set(value)


def reset_correlation_id() -> None:
    """Aktif bağlamdaki korelasyon ID'yi temizler."""
    _current.set(None)
