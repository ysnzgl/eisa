"""
Kampanya URL yönlendirmeleri.
/sync/ endpoint'i DRF router tarafından list action'larından önce oluşturulur.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CampaignViewSet

router = DefaultRouter()
# Boş prefix: /api/campaigns/ → liste, /api/campaigns/{pk}/ → detay
# /api/campaigns/sync/ → kiosk sync action (DRF list action'ı olarak kayıtlı)
router.register(r"", CampaignViewSet, basename="campaign")

urlpatterns = [
    path("", include(router.urls)),
]

