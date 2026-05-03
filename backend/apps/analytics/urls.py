"""Analitik URL yonlendirmeleri. /sessions/stats/ /sessions/'den onceye konmali."""
from django.urls import path

from .views import OturumLoguStatsView, OturumLoguView, ReklamGosterimBulkPushView

urlpatterns = [
    path("sessions/stats/", OturumLoguStatsView.as_view(), name="oturum-stats"),
    path("sessions/", OturumLoguView.as_view(), name="oturum-log"),
    path("impressions/", ReklamGosterimBulkPushView.as_view(), name="reklam-gosterim"),
]
