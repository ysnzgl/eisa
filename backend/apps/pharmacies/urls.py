"""Eczane ve Kiosk URL yonlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .dashboard import EczaciDashboardView
from .views import (
    EczaneViewSet,
    KioskBootstrapView,
    KioskProvisioningApproveView,
    KioskProvisioningDetailView,
    KioskProvisioningListView,
    KioskProvisioningRejectView,
    KioskViewSet,
)

kiosk_router = DefaultRouter()
kiosk_router.register(r"kiosks", KioskViewSet, basename="kiosk")

urlpatterns = [
    path("me/dashboard/", EczaciDashboardView.as_view(), name="eczaci-dashboard"),
    path("kiosks/bootstrap/", KioskBootstrapView.as_view(), name="kiosk-bootstrap"),
    # Admin: onay bekleyen cihaz yonetimi
    path("kiosks/provisioning/", KioskProvisioningListView.as_view(), name="kiosk-provisioning-list"),
    path("kiosks/provisioning/<uuid:pk>/", KioskProvisioningDetailView.as_view(), name="kiosk-provisioning-detail"),
    path("kiosks/provisioning/<uuid:pk>/approve/", KioskProvisioningApproveView.as_view(), name="kiosk-provisioning-approve"),
    path("kiosks/provisioning/<uuid:pk>/reject/", KioskProvisioningRejectView.as_view(), name="kiosk-provisioning-reject"),
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
