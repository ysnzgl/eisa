"""
Hassas veri maskeleme yardımcıları.

Log ve dış çağrı gönderiminden önce alan adları büyük-küçük harf duyarsız
şekilde karşılaştırılır; eşleşen anahtarlar sabit `***` maskesiyle değiştirilir.
Serileştirilemeyen değerler güvenli bir metne dönüştürülür.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, MutableMapping

REDACTED = "***"

# Alan adları büyük-küçük harf duyarsız karşılaştırılır.
DEFAULT_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-csrftoken",
        "csrftoken",
        "csrf_token",
        "x-api-key",
        "x-app-key",
        "x-kiosk-key",
        "x-kiosk-app-key",
        "password",
        "new_password",
        "current_password",
        "confirm_password",
        "secret",
        "app_key",
        "app_key_hash",
        "uygulama_anahtari",
        "fleet_key",
        "kiosk_fleet_key",
        "provisioning_secret",
        "kiosk_provisioning_secret",
        "iot_token",
        "token",
        "access",
        "access_token",
        "refresh",
        "refresh_token",
        "jwt",
        "hmac",
        "signature",
        "sig",
        "connection_string",
        "database_url",
        "db_password",
        "postgres_password",
        "s3_access_key",
        "s3_secret_key",
        "rustfs_access_key",
        "rustfs_secret_key",
        "minio_access_key",
        "minio_secret_key",
        "email",
        "e_mail",
        "telefon",
        "phone",
        "qr_kodu",
        "qr_payload",
        "cevaplar",
        "onerilen_etken_maddeler",
        "raw_body",
        "response_body",
    }
)

# Aşırı büyük değerleri özetle (log satırlarını korumak için).
_MAX_STRING_LEN = 1024
_MAX_COLLECTION_ITEMS = 50


def _is_sensitive(key: Any, extra_keys: Iterable[str]) -> bool:
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    if lowered in DEFAULT_SENSITIVE_KEYS:
        return True
    for extra in extra_keys:
        if lowered == extra.lower():
            return True
    return False


def _truncate_str(value: str) -> str:
    if len(value) > _MAX_STRING_LEN:
        return value[:_MAX_STRING_LEN] + f"…[+{len(value) - _MAX_STRING_LEN}c]"
    return value


def _safe_repr(value: Any) -> str:
    try:
        text = repr(value)
    except Exception:  # pragma: no cover
        text = f"<unrepr {type(value).__name__}>"
    return _truncate_str(text)


def sanitize(value: Any, *, extra_keys: Iterable[str] = ()) -> Any:
    """
    Verilen değeri özyinelemeli olarak temizler.

    - dict / Mapping: hassas anahtarlar maskelenir, iç içe değerler temizlenir.
    - list / tuple / set: her eleman temizlenir; maksimum eleman sayısı sınırlanır.
    - str: aşırı uzun değerler kırpılır.
    - primitif olmayan objeler güvenli repr'a çevrilir.
    """
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _truncate_str(value)
    if isinstance(value, Mapping):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive(key, extra_keys):
                clean[str(key)] = REDACTED
            else:
                clean[str(key)] = sanitize(item, extra_keys=extra_keys)
        return clean
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        truncated = items[:_MAX_COLLECTION_ITEMS]
        cleaned = [sanitize(v, extra_keys=extra_keys) for v in truncated]
        if len(items) > _MAX_COLLECTION_ITEMS:
            cleaned.append(f"…[+{len(items) - _MAX_COLLECTION_ITEMS} more]")
        return cleaned
    return _safe_repr(value)


def sanitize_headers(headers: Mapping[str, Any] | None) -> dict[str, Any]:
    """HTTP başlık sözlüğünü hassas alanları maskeleyerek döner."""
    if not headers:
        return {}
    return {str(k): (REDACTED if _is_sensitive(k, ()) else _truncate_str(str(v)))
            for k, v in headers.items()}


def redact_mapping_in_place(target: MutableMapping[str, Any]) -> None:
    """Mevcut bir dict üzerinde hassas alanları yerinde maskeler."""
    for key in list(target.keys()):
        if _is_sensitive(key, ()):
            target[key] = REDACTED
        else:
            target[key] = sanitize(target[key])
