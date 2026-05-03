"""Merkezi URL yönlendirmesi."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from .auth_views import (
    CookieLogoutView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    # Panel kimlik doğrulama (httpOnly çerez tabanlı JWT) — rate-limited
    path("api/auth/token/", CookieTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/logout/", CookieLogoutView.as_view(), name="token_logout"),
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

