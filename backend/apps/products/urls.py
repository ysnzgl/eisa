"""Ürün URL yönlendirmeleri — kiosk sync ve admin CRUD endpoint'leri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActiveIngredientViewSet,
    AnswerViewSet,
    CategoryViewSet,
    ProductSyncView,
    QuestionViewSet,
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"questions", QuestionViewSet, basename="question")
router.register(r"answers", AnswerViewSet, basename="answer")
router.register(r"ingredients", ActiveIngredientViewSet, basename="ingredient")

urlpatterns = [
    # GET /api/products/sync/ — Kiosk için tam ürün verisi (JWT veya App-Key)
    path("sync/", ProductSyncView.as_view(), name="product-sync"),
    # Admin CRUD endpoint'leri
    path("", include(router.urls)),
]

