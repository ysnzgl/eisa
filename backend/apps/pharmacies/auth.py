"""Kiosk App-Key kimlik doğrulama (JWT yerine kullanılır)."""
from __future__ import annotations

import secrets

from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import Kiosk


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

        kiosk.last_seen_at = timezone.now()
        kiosk.save(update_fields=["last_seen_at"])

        # DRF user/auth ikilisi: (user, auth). Kiosk'u "user" olarak işaretliyoruz.
        return (kiosk, key)
