"""
Eczane ve kiosk URL yönlendirmeleri.
Eczane endpoint'leri int:pk ile çakışmayı önlemek için manuel olarak tanımlanmıştır.
Kiosk endpoint'leri DRF router üzerinden yönetilir.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .dashboard import PharmacistDashboardView
from .views import KioskViewSet, PharmacyViewSet

# Kiosk router'ı: /kiosks/, /kiosks/me/, /kiosks/{pk}/, /kiosks/{pk}/regenerate-key/
kiosk_router = DefaultRouter()
kiosk_router.register(r"kiosks", KioskViewSet, basename="kiosk")

urlpatterns = [
    # Eczacı ana sayfa özeti: GET /api/pharmacies/me/dashboard/
    path(
        "me/dashboard/",
        PharmacistDashboardView.as_view(),
        name="pharmacist-dashboard",
    ),
    # Eczane listesi/oluşturma: GET/POST /api/pharmacies/
    path(
        "",
        PharmacyViewSet.as_view({"get": "list", "post": "create"}),
        name="pharmacy-list",
    ),
    # Eczane detay: GET/PUT/PATCH/DELETE /api/pharmacies/{pk}/
    # int:pk kullanımı "kiosks/" gibi string'lerin yanlış eşleşmesini engeller
    path(
        "<int:pk>/",
        PharmacyViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="pharmacy-detail",
    ),
    # Kiosk endpoint'leri router üzerinden dahil edilir
    path("", include(kiosk_router.urls)),
]

