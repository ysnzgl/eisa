"""Kullanici gorunumleri — JWT korumali profil."""
from rest_framework import generics, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import KullaniciSerializer


class ProfilView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/users/me/ — Kullanici profilini doner/gunceller."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = KullaniciSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user
