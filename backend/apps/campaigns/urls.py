"""Reklam URL yonlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ReklamViewSet

router = DefaultRouter()
router.register(r"", ReklamViewSet, basename="reklam")

urlpatterns = [
    path("", include(router.urls)),
]
