"""
E-ISA ozel izin siniflari.

JWT panel kullanicilari (super admin / eczaci) ve kiosk cihazlari icin.
"""
from rest_framework.permissions import BasePermission

from apps.users.models import Kullanici


class IsSuperAdmin(BasePermission):
    """Sadece 'superadmin' rolune sahip JWT kullanicilarina izin verir."""

    message = "Bu islem icin super admin yetkisi gereklidir."

    def has_permission(self, request, view):
        return bool(
            request.user
            and isinstance(request.user, Kullanici)
            and request.user.rol == Kullanici.Rol.SUPERADMIN
        )


class IsEczaci(BasePermission):
    """Sadece 'pharmacist' rolune sahip JWT kullanicilarina izin verir."""

    message = "Bu islem icin eczaci yetkisi gereklidir."

    def has_permission(self, request, view):
        return bool(
            request.user
            and isinstance(request.user, Kullanici)
            and request.user.rol == Kullanici.Rol.ECZACI
        )


class IsKiosk(BasePermission):
    """Sadece App-Key ile dogrulanmis kiosk cihazlarina izin verir."""

    message = "Bu endpoint sadece kiosk cihazlari icindir."

    def has_permission(self, request, view):
        # KioskAppKeyAuthentication request.auth icine string anahtar koyar
        return isinstance(request.auth, str)


class IsKioskOrAuthenticated(BasePermission):
    """Kiosk (App-Key) veya JWT panel kullanicisi."""

    message = "Kimlik dogrulamasi gereklidir."

    def has_permission(self, request, view):
        if request.user and isinstance(request.user, Kullanici):
            return True
        return isinstance(request.auth, str)


# Geriye donuk uyumluluk takma adlari
IsPharmacist = IsEczaci
