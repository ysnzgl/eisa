"""Reklam (DOOH sponsorluk) URL yonlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MediaUploadView
from .views_v2 import (
    CampaignViewSet,
    CreativeViewSet,
    GenerationJobListView,
    GenerationJobView,
    IdleScreenContentViewSet,
    KioskDayStreamView,
    PharmacyCampaignViewSet,
    PlaylistGenerateView,
    SponsorshipKioskCopyView,
    SponsorshipKioskDetailView,
    SponsorshipKioskListView,
    SponsorshipKioskPreviewView,
    SponsorshipKioskSimulateView,
)

# DOOH v2 router
v2_router = DefaultRouter()
v2_router.register(r"campaigns", CampaignViewSet, basename="dooh-campaign")
v2_router.register(r"creatives", CreativeViewSet, basename="dooh-creative")
v2_router.register(r"idle-contents", IdleScreenContentViewSet, basename="dooh-idle-content")
v2_router.register(r"pharmacy-campaigns", PharmacyCampaignViewSet, basename="pharmacy-campaign")

urlpatterns = [
    # Medya upload (creative icin)
    path("upload-media/", MediaUploadView.as_view(), name="media-upload"),

    # Kiosk-centric sponsorluk yonetimi
    path("v2/sponsorship-kiosks/", SponsorshipKioskListView.as_view(), name="dooh-sponsorship-kiosks"),
    path("v2/sponsorship-kiosks/<int:kiosk_id>/sponsorships/",
         SponsorshipKioskDetailView.as_view(), name="dooh-sponsorship-kiosk-detail"),
    path("v2/sponsorship-kiosks/<int:kiosk_id>/preview/",
         SponsorshipKioskPreviewView.as_view(), name="dooh-sponsorship-kiosk-preview"),
    path("v2/sponsorship-kiosks/<int:kiosk_id>/copy/",
         SponsorshipKioskCopyView.as_view(), name="dooh-sponsorship-kiosk-copy"),
    path("v2/sponsorship-kiosks/<int:kiosk_id>/simulate/",
         SponsorshipKioskSimulateView.as_view(), name="dooh-sponsorship-kiosk-simulate"),

    # Playlist uretim / izleme (JWT, SuperAdmin)
    path("v2/playlists/generate/", PlaylistGenerateView.as_view(), name="dooh-playlist-generate"),
    path("v2/playlists/jobs/", GenerationJobListView.as_view(), name="dooh-playlist-job-list"),
    path("v2/playlists/jobs/<uuid:job_id>/", GenerationJobView.as_view(), name="dooh-playlist-job-detail"),
    path("v2/playlists/day-stream/", KioskDayStreamView.as_view(), name="dooh-kiosk-day-stream"),

    path("v2/", include(v2_router.urls)),
]
