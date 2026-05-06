"""Kullanici URL yonlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import KullaniciViewSet, ProfilView

router = DefaultRouter()
router.register(r"", KullaniciViewSet, basename="kullanici")

urlpatterns = [
    path("me/", ProfilView.as_view(), name="user-profile"),
    path("", include(router.urls)),
]
