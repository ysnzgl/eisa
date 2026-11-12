from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BankaHesabiViewSet, OdemeBilgileriView, SirketProfiliView

router = DefaultRouter()
router.register("banka-hesaplari", BankaHesabiViewSet, basename="sirket-banka-hesabi")

urlpatterns = [
    path("odeme-bilgileri/", OdemeBilgileriView.as_view(), name="sirket-odeme-bilgileri"),
    path("profil/", SirketProfiliView.as_view(), name="sirket-profili"),
    path("", include(router.urls)),
]

