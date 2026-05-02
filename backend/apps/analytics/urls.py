"""
Analitik URL yönlendirmeleri.
Sıralama önemli: /sessions/stats/ mutlaka /sessions/'den önce gelmelidir.
"""
from django.urls import path

from .views import AdImpressionBulkPushView, SessionLogStatsView, SessionLogView

urlpatterns = [
    # GET /api/analytics/sessions/stats/ — Süper admin istatistikleri
    # Bu path /sessions/'den önce tanımlanmalı, aksi hâlde "stats" pk olarak yorumlanır
    path("sessions/stats/", SessionLogStatsView.as_view(), name="session-stats"),
    # GET (admin liste) / POST (kiosk push) /api/analytics/sessions/
    path("sessions/", SessionLogView.as_view(), name="session-log"),
    # POST /api/analytics/impressions/ — Kiosk reklam gösterim verisi
    path("impressions/", AdImpressionBulkPushView.as_view(), name="ad-impression"),
]

