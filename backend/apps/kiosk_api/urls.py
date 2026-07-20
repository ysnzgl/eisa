"""Kiosk API facade — URL yonlendirmeleri (namespace: /api/kiosk/v1/).

Operasyonel endpoint'lerde kiosk ID URL'de YOKTUR; kiosk App Key auth
context'inden (`request.kiosk`) gelir.
"""
from django.urls import path

from .views import (
    KioskBootstrapView,
    KioskCatalogView,
    KioskDiagnosticsView,
    KioskPingView,
    KioskPlaylistView,
    KioskProofOfPlayView,
    KioskSessionsView,
    KioskSyncView,
)

app_name = "kiosk_api"

urlpatterns = [
    # Provisioning (Fleet Key + HMAC)
    path("bootstrap/", KioskBootstrapView.as_view(), name="kiosk-bootstrap"),
    # Operasyonel (AppKey + MAC)
    path("ping/", KioskPingView.as_view(), name="kiosk-ping"),
    path("sync/", KioskSyncView.as_view(), name="kiosk-sync"),
    path("catalog/", KioskCatalogView.as_view(), name="kiosk-catalog"),
    path("playlist/", KioskPlaylistView.as_view(), name="kiosk-playlist"),
    path("sessions/", KioskSessionsView.as_view(), name="kiosk-sessions"),
    path("proof-of-play/", KioskProofOfPlayView.as_view(), name="kiosk-proof-of-play"),
    path("diagnostics/", KioskDiagnosticsView.as_view(), name="kiosk-diagnostics"),
]
