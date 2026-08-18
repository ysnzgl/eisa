"""Analitik URL yonlendirmeleri. /sessions/stats/ /sessions/'den onceye konmali."""
from django.urls import path

from .log_ingest import ClientEventIngestView
from .views import (
    AdminDashboardView,
    CampaignImpressionView,
    KioskActivityView,
    KioskEventListView,
    OturumLoguCompleteView,
    OturumLoguMarkReviewedView,
    DashboardSeriesView,
    OturumLoguStatsView,
    OturumLoguView,
)

urlpatterns = [
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("dashboard-series/", DashboardSeriesView.as_view(), name="dashboard-series"),
    path("sessions/stats/", OturumLoguStatsView.as_view(), name="oturum-stats"),
    path("sessions/<int:pk>/complete/", OturumLoguCompleteView.as_view(), name="oturum-complete"),
    path("sessions/<int:pk>/mark-reviewed/", OturumLoguMarkReviewedView.as_view(), name="oturum-mark-reviewed"),
    path("sessions/", OturumLoguView.as_view(), name="oturum-log"),
    # Kiosk hareketleri — zengin filtreli liste (admin + eczacı)
    path("kiosk-activities/", KioskActivityView.as_view(), name="kiosk-activities"),
    # Kampanya gösterimleri — PlayLog listesi (admin + eczacı)
    path("campaign-impressions/", CampaignImpressionView.as_view(), name="campaign-impressions"),
    # Faz 4: kiosk teknik olayları listesi (admin + eczacı)
    path("kiosk-events/", KioskEventListView.as_view(), name="kiosk-events"),
    # Teknik log ingestion (web panel client hataları) — DB'ye yazılmaz.
    # Kiosk diagnostic ingest artık /api/kiosk/v1/diagnostics/ (kiosk_api facade).
    path("client-events/", ClientEventIngestView.as_view(), name="client-event-ingest"),
]
