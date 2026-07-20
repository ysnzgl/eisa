"""Kiosk API facade — ortak view tabani.

Operasyonel kiosk endpoint'leri `KioskAPIView`'den turer; boylece
authentication, permission ve kiosk context tek yerde yonetilir. View'lar
`self.kiosk` uzerinden dogrulanmis kiosk'a erisir; tekrar App Key sorgusu
yapmaz.
"""
from __future__ import annotations

from rest_framework.views import APIView

from .authentication import KioskAppKeyAuthentication
from .permissions import IsKiosk


class KioskAPIView(APIView):
    """App Key + MAC ile dogrulanan kiosk endpoint'leri icin taban view."""

    authentication_classes = [KioskAppKeyAuthentication]
    permission_classes = [IsKiosk]

    @property
    def kiosk(self):
        """Dogrulanmis kiosk (KioskAppKeyAuthentication tarafindan atanir)."""
        return getattr(self.request, "kiosk", None)
