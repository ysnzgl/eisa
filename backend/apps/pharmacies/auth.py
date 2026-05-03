"""Kiosk App-Key kimlik doğrulama (JWT yerine kullanılır)."""
from __future__ import annotations

import secrets
from datetime import timedelta

from django.utils import timezone
from rest_framework import authentication, exceptions

from apps.audit.models import AuditLog, record as audit_record

from .models import Kiosk


# Bu süreden uzun sessizlikten sonra gelen istekleri "yeniden online" olarak kaydeder.
KIOSK_ONLINE_THRESHOLD = timedelta(minutes=5)


class KioskAppKeyAuthentication(authentication.BaseAuthentication):
    """
    `Authorization: AppKey <key>` başlığı ile kiosk cihazlarını yetkilendirir.

    MAC adresi `X-Kiosk-MAC` başlığında gönderilir ve App-Key ile eşleşmek zorundadır.
    Karşılaştırma constant-time yapılır (timing attack koruması).
    """

    keyword = "AppKey"

    def authenticate(self, request):
        auth = request.headers.get("Authorization", "").split()
        if not auth or auth[0] != self.keyword:
            return None
        if len(auth) != 2:
            raise exceptions.AuthenticationFailed("Geçersiz App-Key başlığı.")

        key = auth[1]
        mac = request.headers.get("X-Kiosk-MAC", "")
        if not mac:
            raise exceptions.AuthenticationFailed("X-Kiosk-MAC başlığı eksik.")

        # MAC public bir tanımlayıcı, indeks ile filtreliyoruz; app_key constant-time karşılaştırılır
        candidates = Kiosk.objects.select_related("pharmacy").filter(
            mac_address=mac, is_active=True
        )
        kiosk = None
        for candidate in candidates:
            if secrets.compare_digest(str(candidate.app_key), key):
                kiosk = candidate
                break
        if kiosk is None:
            raise exceptions.AuthenticationFailed("Kiosk doğrulanamadı.")

        now = timezone.now()
        previous = kiosk.last_seen_at
        kiosk.last_seen_at = now
        kiosk.save(update_fields=["last_seen_at"])

        # Kiosk uzun süre sessiz kaldıktan sonra döndüyse online olayını audit'e yaz.
        if previous is None or (now - previous) > KIOSK_ONLINE_THRESHOLD:
            try:
                fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
                ip = fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")
                audit_record(
                    action=AuditLog.Action.KIOSK_ONLINE,
                    summary=f"Kiosk online: {kiosk.mac_address}",
                    kiosk_mac=kiosk.mac_address,
                    ip_address=ip,
                    metadata={
                        "kiosk_id": kiosk.pk,
                        "previous_seen_at": previous.isoformat() if previous else None,
                    },
                )
            except Exception:  # pragma: no cover - audit yazımı hiç bir zaman istek akışını bozmasın
                pass

        # DRF user/auth ikilisi: (user, auth). Kiosk'u "user" olarak işaretliyoruz.
        return (kiosk, key)
