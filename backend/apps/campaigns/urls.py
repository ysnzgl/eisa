"""Reklam URL yonlendirmeleri."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MediaUploadView, ReklamTakvimViewSet, ReklamViewSet

router = DefaultRouter()
router.register(r"", ReklamViewSet, basename="reklam")

urlpatterns = [
    # upload-media/ önce tanımlanmalı; aksi hâlde DefaultRouter'ın
    # ^(?P<pk>[^/.]+)/$ pattern'i bu path'i pk olarak yakalar ve 405 döner.
    path("upload-media/", MediaUploadView.as_view(), name="media-upload"),
    path(
        "schedules/",
        ReklamTakvimViewSet.as_view({"get": "list", "post": "create"}),
        name="campaign-schedule-list",
    ),
    path(
        "schedules/<int:pk>/",
        ReklamTakvimViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="campaign-schedule-detail",
    ),
    path("", include(router.urls)),
]
