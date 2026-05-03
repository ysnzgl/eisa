"""Kiosk App-Key kimlik dogrulama (JWT yerine kullanilir)."""
from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.utils import timezone
from rest_framework import authentication, exceptions

from apps.audit.models import DenetimLogu, kayit_birak

from .models import Kiosk

logger = logging.getLogger(__name__)

# Bu sureden uzun sessizlikten sonra gelen istekleri "yeniden online" olarak kaydeder.
KIOSK_ONLINE_ESIGI = timedelta(minutes=5)


class KioskAppKeyAuthentication(authentication.BaseAuthentication):
    """
    `Authorization: AppKey <key>` basligi ile kiosk cihazlarini yetkilendirir.
    MAC adresi `X-Kiosk-MAC` basliginda gonderilir; constant-time karsilastirma.
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

        # last_seen guncelleme — UoW kapsam disi (audit alani degil, sadece heartbeat)
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
                logger.exception(
                    "Kiosk online audit kaydi olusturulamadi (mac=%s)",
                    kiosk.mac_adresi,
                )

        return (kiosk, key)
