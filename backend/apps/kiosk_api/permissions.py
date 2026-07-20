"""Kiosk API facade — izinler.

`IsKiosk` kanonik olarak `apps.pharmacies.permissions` icinde tanimlidir;
facade tek noktadan kullansin diye buradan yeniden ihrac edilir.
"""
from __future__ import annotations

from apps.pharmacies.permissions import IsKiosk

__all__ = ["IsKiosk"]
