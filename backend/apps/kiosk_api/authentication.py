"""Kiosk API facade — kimlik dogrulama.

Operasyonel kiosk endpoint'leri (bootstrap disinda) TEK bir contract kullanir::

    Authorization: AppKey <APP_KEY>
    X-Kiosk-MAC:   <NORMALIZED_MAC>

Bootstrap disindaki diger auth turleri bu endpoint'lerde KABUL EDILMEZ.

Kanonik dogrulama sinifi `apps.pharmacies.auth.KioskAppKeyAuthentication`'dir;
tum repoda tek auth sinifi olmasi icin buradan yeniden ihrac edilir. Basarili
dogrulamada `request.kiosk` atanir.
"""
from __future__ import annotations

from apps.pharmacies.auth import KioskAppKeyAuthentication

__all__ = ["KioskAppKeyAuthentication"]
