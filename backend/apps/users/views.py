"""
Kullanıcı görünümleri — JWT korumalı profil endpoint'i.
"""
from rest_framework import generics, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import UserSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/users/me/   — Giriş yapmış kullanıcının profilini döner.
    PATCH /api/users/me/  — E-posta ve eczane bağlantısı gibi alanları günceller.
    PUT desteklenmez; sadece kısmi güncelleme (PATCH) kabul edilir.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    # Tam güncelleme (PUT) devre dışı; sadece GET ve PATCH aktif
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        """İstek sahibi kullanıcıyı doğrudan döndür."""
        return self.request.user
