"""İş takip URL yönlendirmeleri."""
from rest_framework.routers import DefaultRouter

from .views import GorevViewSet

router = DefaultRouter()
router.register(r"gorevler", GorevViewSet, basename="gorev")

urlpatterns = router.urls
