"""Görüş ve Destek URL yönlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DestekParametresiListView, DestekTalebiViewSet

router = DefaultRouter()
router.register(r"talepler", DestekTalebiViewSet, basename="destek-talep")

urlpatterns = [
    path("parametreler/", DestekParametresiListView.as_view(), name="destek-parametreler"),
    path("", include(router.urls)),
]
