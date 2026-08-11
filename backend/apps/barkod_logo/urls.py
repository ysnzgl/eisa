"""Barkod Logo URL yönlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BarkodLogoGorselUploadView, BarkodLogoViewSet

router = DefaultRouter()
router.register(r"logolar", BarkodLogoViewSet, basename="barkod-logo")

urlpatterns = [
    path("upload-gorsel/", BarkodLogoGorselUploadView.as_view(), name="barkod-logo-upload"),
    path("", include(router.urls)),
]
