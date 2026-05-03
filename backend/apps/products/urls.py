"""Urun URL yonlendirmeleri — kiosk sync ve admin CRUD."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CevapViewSet,
    EtkenMaddeViewSet,
    KategoriViewSet,
    SoruViewSet,
    UrunSyncView,
)

router = DefaultRouter()
router.register(r"categories", KategoriViewSet, basename="kategori")
router.register(r"questions", SoruViewSet, basename="soru")
router.register(r"answers", CevapViewSet, basename="cevap")
router.register(r"ingredients", EtkenMaddeViewSet, basename="etken-madde")

urlpatterns = [
    path("sync/", UrunSyncView.as_view(), name="urun-sync"),
    path("", include(router.urls)),
]
