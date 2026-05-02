"""Kullanıcı URL yönlendirmeleri."""
from django.urls import path

from .views import ProfileView

urlpatterns = [
    # GET/PATCH /api/users/me/ — Giriş yapmış kullanıcının profili
    path("me/", ProfileView.as_view(), name="user-profile"),
]

