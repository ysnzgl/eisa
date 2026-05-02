"""Merkezi URL yönlendirmesi."""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Brute-force koruması için login endpoint'inde sıkı rate limit."""
    throttle_scope = "login"


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_scope = "login"


urlpatterns = [
    path("admin/", admin.site.urls),
    # Panel kimlik doğrulama (JWT) — rate-limited
    path("api/auth/token/", ThrottledTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"),
    # Domain API'leri
    path("api/users/", include("apps.users.urls")),
    path("api/pharmacies/", include("apps.pharmacies.urls")),
    path("api/products/", include("apps.products.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/campaigns/", include("apps.campaigns.urls")),
]
