"""Urun URL yonlendirmeleri — kiosk sync ve admin CRUD."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CevapViewSet,
    DanismaViewSet,
    EtkenMaddeViewSet,
    KategoriViewSet,
    SoruEtkenMaddeViewSet,
    SoruViewSet,
    UrunSyncView,
)

router = DefaultRouter()
router.register(r"categories", KategoriViewSet, basename="kategori")
router.register(r"questions", SoruViewSet, basename="soru")
router.register(r"answers", CevapViewSet, basename="cevap")
router.register(r"ingredients", EtkenMaddeViewSet, basename="etken-madde")
router.register(r"question-ingredients", SoruEtkenMaddeViewSet, basename="soru-etken-madde")
router.register(r"danisma", DanismaViewSet, basename="danisma")

urlpatterns = [
    path("sync/", UrunSyncView.as_view(), name="urun-sync"),
    path("", include(router.urls)),
]
