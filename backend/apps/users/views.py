"""Kullanici gorunumleri — JWT korumali profil + admin CRUD."""
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from .models import Kullanici
from .serializers import (
    KullaniciAdminSerializer,
    KullaniciCreateSerializer,
    KullaniciSerializer,
    ResetPasswordSerializer,
)


class IsSuperAdmin(permissions.BasePermission):
    """Yalnızca rol='superadmin' kullanıcılar erişebilir."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and getattr(u, "rol", None) == "superadmin")


class ProfilView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/users/me/ — Kullanici profilini doner/gunceller."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = KullaniciSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class KullaniciViewSet(viewsets.ModelViewSet):
    """Admin CRUD — /api/users/

    Sadece superadmin kullanabilir. Silme = soft delete (is_active=False).
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    queryset = Kullanici.objects.select_related("eczane").order_by("-date_joined")

    def get_serializer_class(self):
        if self.action == "create":
            return KullaniciCreateSerializer
        if self.action == "reset_password":
            return ResetPasswordSerializer
        return KullaniciAdminSerializer

    def perform_destroy(self, instance):
        # Soft delete: pasifleştir, kayıt korunur.
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        user = self.get_object()
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Parola güncellendi."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response(KullaniciAdminSerializer(user).data)

