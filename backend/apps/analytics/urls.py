"""Analitik URL yonlendirmeleri. /sessions/stats/ /sessions/'den onceye konmali."""
from django.urls import path

from .log_ingest import ClientEventIngestView
from .views import (
    AdminDashboardView,
    OturumLoguCompleteView,
    OturumLoguStatsView,
    OturumLoguView,
)

urlpatterns = [
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("sessions/stats/", OturumLoguStatsView.as_view(), name="oturum-stats"),
    path("sessions/<int:pk>/complete/", OturumLoguCompleteView.as_view(), name="oturum-complete"),
    path("sessions/", OturumLoguView.as_view(), name="oturum-log"),
    # Teknik log ingestion (web panel client hataları) — DB'ye yazılmaz.
    # Kiosk diagnostic ingest artık /api/kiosk/v1/diagnostics/ (kiosk_api facade).
    path("client-events/", ClientEventIngestView.as_view(), name="client-event-ingest"),
]
