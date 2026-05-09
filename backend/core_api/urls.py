"""Merkezi URL yönlendirmesi."""
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views import View

from apps.campaigns.urls import inventory_urlpatterns, kiosk_v1_urlpatterns

from .auth_views import (
    CookieLogoutView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
)


class _SilentEmpty(View):
    """/ ve /favicon.ico için log kirliliği olmadan 204 döner."""

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=204)


urlpatterns = [
    path("", _SilentEmpty.as_view()),
    path("favicon.ico", _SilentEmpty.as_view()),
    path("admin/", admin.site.urls),
    # Panel kimlik doğrulama (httpOnly çerez tabanlı JWT) — rate-limited
    path("api/auth/token/", CookieTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/logout/", CookieLogoutView.as_view(), name="token_logout"),
    # Domain API'leri
    path("api/lookups/", include("apps.lookups.urls")),
    path("api/users/", include("apps.users.urls")),
    path("api/pharmacies/", include("apps.pharmacies.urls")),
    path("api/products/", include("apps.products.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/campaigns/", include("apps.campaigns.urls")),
    path("api/inventory/", include((inventory_urlpatterns, "inventory"))),
    path("api/kiosk/v1/", include((kiosk_v1_urlpatterns, "kiosk_v1"))),
]

# Swagger / ReDoc yalnızca geliştirme ortamında
if settings.DEBUG:
    from django.conf.urls.static import static
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
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

