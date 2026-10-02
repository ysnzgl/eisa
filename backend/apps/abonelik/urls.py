"""Abonelik URL yönlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FaturalarimView,
    FaturaOdeView,
    FaturaViewSet,
    FiyatTanimiViewSet,
    HareketlerimView,
    HesabimView,
    OdemelerimView,
    OdemelerView,
    SozlesmeIslakImzaIndir,
    SozlesmeMetniView,
    SozlesmeOnaylaView,
    SozlesmeTalebiViewSet,
    SozlesmeViewSet,
    TaleplerimView,
)

router = DefaultRouter()
router.register(r"sozlesmeler", SozlesmeViewSet, basename="abonelik-sozlesme")
router.register(r"faturalar", FaturaViewSet, basename="abonelik-fatura")
router.register(r"fiyatlar", FiyatTanimiViewSet, basename="abonelik-fiyat")
router.register(r"talepler", SozlesmeTalebiViewSet, basename="abonelik-talep")
router.register(r"odemeler", OdemelerView, basename="abonelik-odeme")

urlpatterns = [
    path("hesabim/", HesabimView.as_view(), name="abonelik-hesabim"),
    path("faturalarim/", FaturalarimView.as_view(), name="abonelik-faturalarim"),
    path("faturalarim/<int:pk>/ode/", FaturaOdeView.as_view(), name="abonelik-fatura-ode"),
    path("odemelerim/", OdemelerimView.as_view(), name="abonelik-odemelerim"),
    path("hareketlerim/", HareketlerimView.as_view(), name="abonelik-hareketlerim"),
    path("taleplerim/", TaleplerimView.as_view(), name="abonelik-taleplerim"),
    path("sozlesmelerim/<int:pk>/onayla/", SozlesmeOnaylaView.as_view(), name="abonelik-sozlesme-onayla"),
    path("sozlesmelerim/<int:pk>/metin/", SozlesmeMetniView.as_view(), name="abonelik-sozlesme-metin-eczaci"),
    path("sozlesmeler/<int:pk>/islak-imza-indir/", SozlesmeIslakImzaIndir.as_view(), name="abonelik-sozlesme-islak-imza-indir"),
    path("", include(router.urls)),
]
