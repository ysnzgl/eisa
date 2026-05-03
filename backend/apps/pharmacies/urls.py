"""Eczane ve Kiosk URL yonlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .dashboard import EczaciDashboardView
from .views import EczaneViewSet, KioskViewSet

kiosk_router = DefaultRouter()
kiosk_router.register(r"kiosks", KioskViewSet, basename="kiosk")

urlpatterns = [
    path("me/dashboard/", EczaciDashboardView.as_view(), name="eczaci-dashboard"),
    path(
        "",
        EczaneViewSet.as_view({"get": "list", "post": "create"}),
        name="eczane-list",
    ),
    path(
        "<int:pk>/",
        EczaneViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="eczane-detail",
    ),
    path("", include(kiosk_router.urls)),
]
