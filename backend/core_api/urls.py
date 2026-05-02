"""Merkezi URL yönlendirmesi."""
from django.conf import settings
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

# Swagger / ReDoc yalnızca geliştirme ortamında
if settings.DEBUG:
    from drf_spectacular.views import (
        SpectacularAPIView,
        SpectacularRedocView,
        SpectacularSwaggerView,
    )

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    ]

