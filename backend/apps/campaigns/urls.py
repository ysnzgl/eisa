"""Reklam URL yonlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MediaUploadView, ReklamTakvimViewSet, ReklamViewSet
from .views_v2 import (
    CampaignViewSet,
    CreativeViewSet,
    HouseAdViewSet,
    InventoryAvailabilityView,
    KioskPlaylistView,
    KioskSyncView,
    PlaylistGenerateView,
    PricingMatrixView,
    ProofOfPlayView,
    ScheduleRuleViewSet,
)

router = DefaultRouter()
router.register(r"", ReklamViewSet, basename="reklam")

# DOOH v2 router (yeni mimariye uygun)
v2_router = DefaultRouter()
v2_router.register(r"campaigns", CampaignViewSet, basename="dooh-campaign")
v2_router.register(r"creatives", CreativeViewSet, basename="dooh-creative")
v2_router.register(r"rules", ScheduleRuleViewSet, basename="dooh-schedule-rule")
v2_router.register(r"house-ads", HouseAdViewSet, basename="dooh-house-ad")

urlpatterns = [
    # ── DOOH v2 yonetim API'si (JWT, SuperAdmin) ──
    path("v2/pricing-matrix/", PricingMatrixView.as_view(), name="dooh-pricing-matrix"),
    path("v2/playlists/generate/", PlaylistGenerateView.as_view(), name="dooh-playlist-generate"),
    path("v2/", include(v2_router.urls)),

    # ── Legacy: upload-media/ ve reklam takvimi (geri uyumluluk) ──
    # upload-media/ önce tanımlanmalı; aksi hâlde DefaultRouter'ın
    # ^(?P<pk>[^/.]+)/$ pattern'i bu path'i pk olarak yakalar ve 405 döner.
    path("upload-media/", MediaUploadView.as_view(), name="media-upload"),
    path(
        "schedules/",
        ReklamTakvimViewSet.as_view({"get": "list", "post": "create"}),
        name="campaign-schedule-list",
    ),
    path(
        "schedules/<int:pk>/",
        ReklamTakvimViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="campaign-schedule-detail",
    ),
    path("", include(router.urls)),
]


# ── Bagimsiz URL kumeleri (core_api/urls.py icinde mount edilir) ──

inventory_urlpatterns = [
    path("availability/", InventoryAvailabilityView.as_view(), name="dooh-inventory-availability"),
]

kiosk_v1_urlpatterns = [
    path("<int:kiosk_id>/sync/", KioskSyncView.as_view(), name="kiosk-sync-v1"),
    path("<int:kiosk_id>/playlist/", KioskPlaylistView.as_view(), name="kiosk-playlist-v1"),
    path("<int:kiosk_id>/proof-of-play/", ProofOfPlayView.as_view(), name="kiosk-pop-v1"),
]

