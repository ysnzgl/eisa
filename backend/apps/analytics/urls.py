"""Analitik URL yonlendirmeleri. /sessions/stats/ /sessions/'den onceye konmali."""
from django.urls import path

from .views import AdminDashboardView, OturumLoguStatsView, OturumLoguView

urlpatterns = [
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("sessions/stats/", OturumLoguStatsView.as_view(), name="oturum-stats"),
    path("sessions/", OturumLoguView.as_view(), name="oturum-log"),
]
