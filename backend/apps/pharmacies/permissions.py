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
    """Kiosk (App-Key) veya JWT panel kullanicisi (superadmin / eczaci; editor HARIC)."""

    message = "Kimlik dogrulamasi gereklidir."

    def has_permission(self, request, view):
        if request.user and isinstance(request.user, Kullanici):
            return request.user.rol in (Kullanici.Rol.SUPERADMIN, Kullanici.Rol.ECZACI)
        return isinstance(request.auth, str)


class IsSuperAdminOrEczaci(BasePermission):
    """
    Eczane paneli kullanicisi: superadmin veya eczaci.

    `editor` rolu (yalnizca web sitesi yonetimi) bilincli olarak HARIC tutulur; eskiden
    `IsAuthenticated` ile acik olan eczane/destek/katalog okuma uclari bunu kullanir.
    """

    message = "Bu islem icin eczaci veya super admin yetkisi gereklidir."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and isinstance(user, Kullanici)
            and user.rol in (Kullanici.Rol.SUPERADMIN, Kullanici.Rol.ECZACI)
        )


# Geriye donuk uyumluluk takma adlari
IsPharmacist = IsEczaci


def _eczaci_panel_kisitli(user) -> bool:
    """Eczacının paneli kısıtlı mı (sözleşmesiz veya ödeme gecikmiş)?"""
    from apps.abonelik.services import panel_kisitli

    kisitli, _ = panel_kisitli(getattr(user, "eczane_id", None))
    return kisitli


class IsEczaciPanelAcik(BasePermission):
    """Eczaci + paneli kısıtlı DEĞİL (sözleşme/ödeme durumu uygun)."""

    message = "Sözleşme veya ödeme durumunuz nedeniyle bu bölüm kısıtlanmıştır."

    def has_permission(self, request, view):
        user = request.user
        if not (user and isinstance(user, Kullanici) and user.rol == Kullanici.Rol.ECZACI):
            return False
        return not _eczaci_panel_kisitli(user)


class PanelAcikVeyaAdmin(BasePermission):
    """SuperAdmin her zaman; eczaci yalnızca paneli açıkken."""

    message = "Sözleşme veya ödeme durumunuz nedeniyle bu bölüm kısıtlanmıştır."

    def has_permission(self, request, view):
        user = request.user
        if not (user and isinstance(user, Kullanici)):
            return False
        if user.rol == Kullanici.Rol.SUPERADMIN:
            return True
        if user.rol == Kullanici.Rol.ECZACI:
            return not _eczaci_panel_kisitli(user)
        return False
