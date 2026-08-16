"""Merkezi URL yönlendirmesi."""
from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path
from django.views import View

from apps.campaigns.urls import inventory_urlpatterns

from .auth_views import (
    CookieLogoutView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
)


class _SilentEmpty(View):
    """/ ve /favicon.ico için log kirliliği olmadan 204 döner."""

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=204)


class _Healthz(View):
    """K8s liveness probe — DB'ye dokunmaz, hızlı 200 döner."""

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, *args, **kwargs):
        return HttpResponse("ok", content_type="text/plain", status=200)


class _Readyz(View):
    """K8s readiness probe — DB bağlantısını denetler, JSON döner."""

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request, *args, **kwargs):
        from django.db import connections

        checks: dict = {}
        http_status = 200
        try:
            conn = connections["default"]
            conn.ensure_connection()
            checks["db"] = "ok"
        except Exception:
            checks["db"] = "error"
            http_status = 503

        overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
        return JsonResponse({"status": overall, "components": checks}, status=http_status)


urlpatterns = [
    path("", _SilentEmpty.as_view()),
    path("favicon.ico", _SilentEmpty.as_view()),
    path("healthz", _Healthz.as_view()),
    path("healthz/", _Healthz.as_view()),
    path("readyz", _Readyz.as_view()),
    path("readyz/", _Readyz.as_view()),
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
    path("api/kiosk/v1/", include("apps.kiosk_api.urls")),
    path("api/barkod-logo/", include("apps.barkod_logo.urls")),
    path("api/destek/", include("apps.destek.urls")),
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

