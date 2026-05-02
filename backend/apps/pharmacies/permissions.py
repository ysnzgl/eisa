"""
E-İSA özel izin sınıfları.
JWT panel kullanıcıları (süper admin / eczacı) ve kiosk cihazları için.
"""
from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Sadece 'superadmin' rolüne sahip JWT kullanıcılarına izin verir."""

    message = "Bu işlem için süper admin yetkisi gereklidir."

    def has_permission(self, request, view):
        return bool(
            request.user
            and hasattr(request.user, "role")
            and request.user.role == "superadmin"
        )


class IsPharmacist(BasePermission):
    """Sadece 'pharmacist' rolüne sahip JWT kullanıcılarına izin verir."""

    message = "Bu işlem için eczacı yetkisi gereklidir."

    def has_permission(self, request, view):
        return bool(
            request.user
            and hasattr(request.user, "role")
            and request.user.role == "pharmacist"
        )


class IsKiosk(BasePermission):
    """
    Sadece App-Key ile doğrulanmış kiosk cihazlarına izin verir.
    KioskAppKeyAuthentication başarılı olduğunda request.auth bir string (app_key) olur.
    """

    message = "Bu endpoint sadece kiosk cihazları içindir."

    def has_permission(self, request, view):
        return isinstance(request.auth, str)


class IsKioskOrAuthenticated(BasePermission):
    """
    Kiosk (App-Key) veya JWT ile doğrulanmış panel kullanıcılarına izin verir.
    Hem kiosk hem admin panelin erişebildiği endpoint'ler için kullanılır.
    """

    message = "Kimlik doğrulama gereklidir."

    def has_permission(self, request, view):
        # JWT ile doğrulanmış panel kullanıcısı kontrolü
        if request.user and hasattr(request.user, "role"):
            return True
        # App-Key ile doğrulanmış kiosk cihazı kontrolü
        return isinstance(request.auth, str)
