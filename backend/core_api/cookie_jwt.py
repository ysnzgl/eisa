"""
JWT cookie tabanlı kimlik doğrulama.

Panel'lerin (Vue 3) JWT erişim token'ını `httpOnly + Secure + SameSite=Strict`
çerez olarak saklamasını sağlar. Bu, XSS ile token sızıntısını engeller
(SEC-002).

`Authorization: Bearer ...` başlığı geriye dönük uyumluluk için hâlâ kabul
edilir (örn. otomatik testler / curl). Üretim panel istemcileri çerez yolunu
kullanır.
"""
from __future__ import annotations

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTCookieAuthentication(JWTAuthentication):
    """JWT token'ını önce çerezden, yoksa Authorization başlığından okur."""

    def authenticate(self, request):
        header = self.get_header(request)
        raw_token = self.get_raw_token(header) if header is not None else None

        if raw_token is None:
            cookie_name = getattr(settings, "JWT_AUTH_COOKIE", "eisa_access")
            raw_cookie = request.COOKIES.get(cookie_name)
            if not raw_cookie:
                return None
            raw_token = raw_cookie.encode("utf-8") if isinstance(raw_cookie, str) else raw_cookie

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
