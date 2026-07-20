"""Reklam (DOOH v2) URL yonlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MediaUploadView
from .views_v2 import (
    CampaignViewSet,
    CreativeViewSet,
    DayPlanViewSet,
    GenerationJobListView,
    GenerationJobView,
    HouseAdViewSet,
    HourPlanViewSet,
    InventoryAvailabilityView,
    PlaylistGenerateView,
    PlaylistTemplateViewSet,
    PricingMatrixView,
    ScheduleRuleViewSet,
)

# DOOH v2 router
v2_router = DefaultRouter()
v2_router.register(r"campaigns", CampaignViewSet, basename="dooh-campaign")
v2_router.register(r"creatives", CreativeViewSet, basename="dooh-creative")
v2_router.register(r"rules", ScheduleRuleViewSet, basename="dooh-schedule-rule")
v2_router.register(r"house-ads", HouseAdViewSet, basename="dooh-house-ad")
v2_router.register(r"playlist-templates", PlaylistTemplateViewSet, basename="dooh-playlist-template")
v2_router.register(r"hour-plans", HourPlanViewSet, basename="dooh-hour-plan")
v2_router.register(r"day-plans", DayPlanViewSet, basename="dooh-day-plan")

urlpatterns = [
    # Medya upload (creative + house ad icin ortak)
    path("upload-media/", MediaUploadView.as_view(), name="media-upload"),

    # DOOH v2 yonetim API'si (JWT, SuperAdmin)
    path("v2/pricing-matrix/", PricingMatrixView.as_view(), name="dooh-pricing-matrix"),
    path("v2/playlists/generate/", PlaylistGenerateView.as_view(), name="dooh-playlist-generate"),
    path("v2/playlists/jobs/", GenerationJobListView.as_view(), name="dooh-playlist-job-list"),
    path("v2/playlists/jobs/<uuid:job_id>/", GenerationJobView.as_view(), name="dooh-playlist-job-detail"),
    path("v2/", include(v2_router.urls)),
]


# ── Bagimsiz URL kumeleri (core_api/urls.py icinde mount edilir) ──

inventory_urlpatterns = [
    path("availability/", InventoryAvailabilityView.as_view(), name="dooh-inventory-availability"),
]
