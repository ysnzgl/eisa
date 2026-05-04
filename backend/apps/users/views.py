"""Kullanici gorunumleri â€” JWT korumali profil."""
from rest_framework import generics, permissions
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from .serializers import KullaniciSerializer


class ProfilView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/users/me/ â€” Kullanici profilini doner/gunceller."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = KullaniciSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

