"""Kiosk kimlik dogrulama.

Operasyonel endpoint'ler icin TEK contract::
    Authorization: AppKey <APP_KEY>
    X-Kiosk-MAC:   <NORMALIZED_MAC>

Provisioning (bootstrap) icin ayri dogrulama (kiosk_api.views.KioskBootstrapView):
  - Kiosk: HMAC-SHA256(MAC_UPPER + iso_timestamp, KIOSK_PROVISIONING_SECRET) + X-Kiosk-Key (fleet).
  - Backend: fleet key + HMAC + timestamp tazelik kontrolu yapar.

Bu endpoint'lerde App Key + MAC disinda kimlik kullanilmaz.
"""
from __future__ import annotations

import hashlib
import hmac as _hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone as _tz

from django.conf import settings
from django.utils import timezone
from rest_framework import authentication, exceptions

from apps.audit.models import DenetimLogu, kayit_birak

from .models import Kiosk


# â”€â”€ Legacy provisioning temizligi (App Key'e gecildi) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# â”€â”€ Provision HMAC dogrulama â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def verify_provision_hmac(mac: str, iso_timestamp: str, received_hmac: str, secret: str, device_id: str = "") -> bool:
    """HMAC-SHA256(MAC_UPPER + iso_timestamp + device_id, secret) karsilastirir.

    device_id: Kalici cihaz UUID (spoofing onleme). Eski sistemlerde bos olabilir (legacy uyum).
    """
    message = mac.upper() + iso_timestamp + device_id
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


# â”€â”€ Fleet key yardimcisi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


def normalize_mac(raw: str) -> str:
    """MAC'i tek bicime getirir: buyuk harf + ':' ayirici (AA:BB:CC:DD:EE:FF)."""
    return (raw or "").strip().upper().replace("-", ":")


class KioskAppKeyAuthentication(authentication.BaseAuthentication):
    """App Key + MAC ile kiosk kimlik dogrulama (TEK operasyonel yontem).

    Contract::
        Authorization: AppKey <APP_KEY>
        X-Kiosk-MAC:   <MAC>

    Bearer / IoT / JWT / Fleet key bu yol icin gecersizdir. Basarili
    dogrulamada ``request.kiosk`` atanir ve ``(kiosk, app_key)`` doner.

    Durum kodlari:
      401 â€” App Key/MAC eksik veya App Key gecersiz (kimlik saglanamadi).
      403 â€” Kiosk pasif/onaysiz veya eczaneye bagli degil (yetki yok).
    """

    keyword = "AppKey"

    def authenticate_header(self, request):
        # Kimlik saglanamadiginda DRF'nin 401 (403 degil) donmesini saglar.
        return self.keyword

    def authenticate(self, request):
        auth = request.headers.get("Authorization", "").split()
        # Bu contract disinda bir sema (Bearer vb.) => bu authenticator kimlik saglamaz.
        if not auth or auth[0] != self.keyword:
            return None
        if len(auth) != 2:
            raise exceptions.AuthenticationFailed(
                {"detail": "Gecersiz App-Key basligi.", "code": "app_key_malformed"}
            )
        key = auth[1]

        mac = normalize_mac(request.headers.get("X-Kiosk-MAC", ""))
        if not mac:
            raise exceptions.AuthenticationFailed(
                {"detail": "X-Kiosk-MAC basligi eksik.", "code": "mac_missing"}
            )

        device_id = request.headers.get("X-Kiosk-Device-ID", "").strip()

        # MAC ile kiosk bul (aktif filtresi YOK; once App Key dogrula, sonra durum).
        kiosk = Kiosk.objects.select_related("eczane").filter(mac_adresi=mac).first()
        if kiosk is None or not secrets.compare_digest(str(kiosk.uygulama_anahtari), key):
            # MAC/App Key cifti gecersiz â€” hangi tarafin hatali oldugu belirtilmez.
            raise exceptions.AuthenticationFailed(
                {"detail": "Kimlik dogrulanamadi.", "code": "app_key_invalid"}
            )

        # Device ID validation: eger kiosk'ta device_id set edilmisse match olmali
        if kiosk.device_id:
            if not device_id:
                raise exceptions.AuthenticationFailed(
                    {"detail": "X-Kiosk-Device-ID basligi eksik.", "code": "device_id_missing"}
                )
            if not secrets.compare_digest(kiosk.device_id, device_id):
                raise exceptions.AuthenticationFailed(
                    {"detail": "Device ID eslesmedi.", "code": "device_id_mismatch"}
                )

        # App Key gecerli; yetki/durum kontrolleri => 403.
        if not kiosk.aktif:
            raise exceptions.PermissionDenied(
                {"detail": "Kiosk pasif veya onaysiz.", "code": "kiosk_inactive"}
            )
        if kiosk.eczane_id is None:
            raise exceptions.PermissionDenied(
                {"detail": "Kiosk bir eczaneye bagli degil.", "code": "kiosk_unlinked"}
            )

        _update_last_seen(kiosk, request)
        request.kiosk = kiosk
        return (kiosk, key)
