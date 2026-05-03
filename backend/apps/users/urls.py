"""Kullanici URL yonlendirmeleri."""
from django.urls import path

from .views import ProfilView

urlpatterns = [
    path("me/", ProfilView.as_view(), name="user-profile"),
]
