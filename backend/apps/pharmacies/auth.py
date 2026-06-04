"""Kiosk kimlik dogrulama.

Iki katmanli IoT auth modeli:
  1. X-Kiosk-Key  : Fleet anahtari — tum cihazlarda ayni, her istekte gonder.
  2. IoT Token    : Per-device, TTL'li, provision sonrasi verilir.
                    Header: Authorization: Bearer <token>

Provision akisi:
  - Kiosk: HMAC-SHA256(MAC_UPPER + iso_timestamp, KIOSK_PROVISIONING_SECRET) gonderir.
  - Backend: HMAC dogrular, timestamp tazelik kontrolu yapar, IoT token verir.
"""
from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import json
import logging
import secrets
import time as _time
from datetime import datetime, timedelta, timezone as _tz

from django.conf import settings
from django.utils import timezone
from rest_framework import authentication, exceptions

from apps.audit.models import DenetimLogu, kayit_birak

from .models import Kiosk


# ── IoT Token (HMAC-SHA256 imzali, base64url payload) ────────────────────────

def _provisioning_secret() -> str:
    return getattr(settings, "KIOSK_PROVISIONING_SECRET", "") or ""


def create_iot_token(kiosk_id: int, pharmacy_id: int, mac: str) -> str:
    """Kiosk icin imzali IoT token uretir."""
    secret = _provisioning_secret()
    ttl_days: int = getattr(settings, "KIOSK_IOT_TOKEN_TTL_DAYS", 7)
    exp = int(_time.time()) + ttl_days * 86400
    payload = json.dumps(
        {"kiosk_id": kiosk_id, "pharmacy_id": pharmacy_id, "mac": mac.upper(), "exp": exp},
        separators=(",", ":"),
        sort_keys=True,
    )
    payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    sig = _hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_iot_token(token: str) -> dict | None:
    """Token'i dogrular; gecersiz/suresi dolmussa None doner."""
    secret = _provisioning_secret()
    if not secret or not token:
        return None
    try:
        payload_b64, sig = token.rsplit(".", 1)
        expected = _hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(sig, expected):
            return None
        padding = 4 - len(payload_b64) % 4
        padded = payload_b64 + "=" * (padding % 4)
        data = json.loads(base64.urlsafe_b64decode(padded).decode())
        if data.get("exp", 0) < _time.time():
            return None
        return data
    except Exception:
        return None


# ── Provision HMAC dogrulama ─────────────────────────────────────────────────

def verify_provision_hmac(mac: str, iso_timestamp: str, received_hmac: str, secret: str) -> bool:
    """HMAC-SHA256(MAC_UPPER + iso_timestamp, secret) karsilastirir."""
    message = mac.upper() + iso_timestamp
    expected = _hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return _hmac.compare_digest(expected, received_hmac)


def is_timestamp_fresh(iso_timestamp: str, tolerance_sec: int = 300) -> bool:
    """Timestamp'in +/- tolerance_sec icinde oldugunu dogrular (replay koruyu)."""
    try:
        ts = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        diff = abs((datetime.now(_tz.utc) - ts).total_seconds())
        return diff <= tolerance_sec
    except Exception:
        return False


# ── Fleet key yardimcisi ─────────────────────────────────────────────────────

def check_fleet_key(request) -> bool:
    """X-Kiosk-Key header'ini KIOSK_FLEET_KEY ile karsilastirir."""
    fleet_key = getattr(settings, "KIOSK_FLEET_KEY", "") or ""
    if not fleet_key:
        return True  # ayarlanmamissa kontrol atlaniyor (dev ortami)
    provided = (request.headers.get("X-Kiosk-Key") or "").strip()
    if not provided:
        return False
    return secrets.compare_digest(provided, fleet_key)

logger = logging.getLogger(__name__)

# Bu sureden uzun sessizlikten sonra gelen istekleri "yeniden online" olarak kaydeder.
KIOSK_ONLINE_ESIGI = timedelta(minutes=5)


def _update_last_seen(kiosk: "Kiosk", request) -> None:
    """Heartbeat guncelleme + audit log (ortak)."""
    now = timezone.now()
    previous = kiosk.son_goruldu
    Kiosk.objects.filter(pk=kiosk.pk).update(son_goruldu=now)
    kiosk.son_goruldu = now
    if previous is None or (now - previous) > KIOSK_ONLINE_ESIGI:
        try:
            fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
            ip = fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")
            kayit_birak(
                eylem=DenetimLogu.Eylem.KIOSK_ONLINE,
                ozet=f"Kiosk online: {kiosk.mac_adresi}",
                kiosk_mac=kiosk.mac_adresi,
                ip_adresi=ip,
                metadata={
                    "kiosk_id": kiosk.pk,
                    "previous_seen_at": previous.isoformat() if previous else None,
                },
            )
        except Exception:  # pragma: no cover
            logger.exception("Kiosk online audit kaydi olusturulamadi (mac=%s)", kiosk.mac_adresi)


class KioskIoTTokenAuthentication(authentication.BaseAuthentication):
    """IoT token (Bearer) + X-Kiosk-Key fleet anahtari ile kimlik dogrulama.

    Her istekte:
      - X-Kiosk-Key: <KIOSK_FLEET_KEY>          (fleet kimlik)
      - Authorization: Bearer <iot_token>        (cihaz kimlik, TTL'li)
    """

    def authenticate(self, request):
        # Fleet key kontrolu
        if not check_fleet_key(request):
            return None  # kiosk istegi degil

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:].strip()

        data = verify_iot_token(token)
        if data is None:
            raise exceptions.AuthenticationFailed(
                "Gecersiz veya suresi dolmus IoT token. Yeniden provision gerekiyor."
            )

        kiosk_id = data.get("kiosk_id")
        try:
            kiosk = Kiosk.objects.select_related("eczane").get(pk=kiosk_id, aktif=True)
        except Kiosk.DoesNotExist:
            raise exceptions.AuthenticationFailed("IoT token'a ait kiosk bulunamadi veya pasif.")

        _update_last_seen(kiosk, request)
        return (kiosk, token)


class KioskAppKeyAuthentication(authentication.BaseAuthentication):
    """Legacy: `Authorization: AppKey <key>` ile kimlik dogrulama.
    Geriye donuk uyumluluk icin korunur. Yeni cihazlar IoT token kullanmali.
    """

    keyword = "AppKey"

    def authenticate(self, request):
        auth = request.headers.get("Authorization", "").split()
        if not auth or auth[0] != self.keyword:
            return None
        if len(auth) != 2:
            raise exceptions.AuthenticationFailed("Gecersiz App-Key basligi.")

        key = auth[1]
        mac = request.headers.get("X-Kiosk-MAC", "")
        if not mac:
            raise exceptions.AuthenticationFailed("X-Kiosk-MAC basligi eksik.")

        candidates = Kiosk.objects.select_related("eczane").filter(
            mac_adresi=mac, aktif=True
        )
        kiosk = None
        for candidate in candidates:
            if secrets.compare_digest(str(candidate.uygulama_anahtari), key):
                kiosk = candidate
                break
        if kiosk is None:
            raise exceptions.AuthenticationFailed("Kiosk dogrulanamadi.")

        _update_last_seen(kiosk, request)
        return (kiosk, key)
