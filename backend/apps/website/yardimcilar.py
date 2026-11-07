"""Ortak yardımcılar: Türkçe slug, istemci IP'si ve IP hash'i."""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re

from django.conf import settings
from django.utils.crypto import constant_time_compare
from django.utils.text import slugify

SLUG_RE = re.compile(r"^[a-z0-9-]+$")
_TR_HARITA = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "I": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})

_DEV_SERVER_TOKEN = "dev-website-token"


def tr_slugify(metin: str) -> str:
    return slugify((metin or "").translate(_TR_HARITA))[:100].strip("-")


def _gecerli_ip(deger: str) -> str | None:
    try:
        return str(ipaddress.ip_address((deger or "").strip()))
    except ValueError:
        return None


def site_sunucusu_mu(request) -> bool:
    """X-Website-Token, WEBSITE_SERVER_TOKEN ile eşleşiyor mu? (sabit zamanlı karşılaştırma)"""
    beklenen = getattr(settings, "WEBSITE_SERVER_TOKEN", "") or ""
    if not beklenen:
        return False
    # Üretimde (DEBUG=False) geliştirme varsayılan token'ı ile IP beyanı kabul edilmez;
    # aksi halde herkes X-Website-Client-IP ile throttle'ı atlatabilirdi.
    if not settings.DEBUG and beklenen == _DEV_SERVER_TOKEN:
        return False
    gelen = request.META.get("HTTP_X_WEBSITE_TOKEN", "") or ""
    return bool(gelen) and constant_time_compare(gelen, beklenen)


def istemci_ip(request) -> str:
    """
    CONTRACT §3: X-Website-Token eşleşirse X-Website-Client-IP, aksi halde REMOTE_ADDR.
    (X-Forwarded-For'a güvenilmez.)
    """
    if site_sunucusu_mu(request):
        beyan = _gecerli_ip(request.META.get("HTTP_X_WEBSITE_CLIENT_IP", ""))
        if beyan:
            return beyan
    return request.META.get("REMOTE_ADDR", "") or ""


def ip_hash(ip: str) -> str:
    """IP ham saklanmaz: SECRET_KEY ile anahtarlanmış SHA-256 (HMAC)."""
    if not ip:
        return ""
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), ip.encode("utf-8"), hashlib.sha256).hexdigest()
