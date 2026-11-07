"""Web sitesi izin sınıfları."""
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission

from apps.users.models import Kullanici

from .yardimcilar import site_sunucusu_mu

WEBSITE_ROLLERI = (Kullanici.Rol.SUPERADMIN, Kullanici.Rol.EDITOR)


class IsWebsiteEditor(BasePermission):
    """Web sitesi yönetimi: rol `superadmin` veya `editor` (CONTRACT §5)."""

    message = "Bu işlem için web sitesi editörü yetkisi gereklidir."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and isinstance(user, Kullanici)
            and user.is_active
            and user.rol in WEBSITE_ROLLERI
        )


class IsWebsiteSunucusu(BasePermission):
    """
    Public ve önizleme uçları yalnızca site sunucusuna (Next.js, cluster içi) açıktır:
    `X-Website-Token` = WEBSITE_SERVER_TOKEN zorunludur (sabit zamanlı karşılaştırma).
    Token yoksa/yanlışsa 404 döner — uçların varlığı dışarıya sızdırılmaz.
    Üretimde geliştirme varsayılan token'ı kabul edilmez (fail-closed).
    """

    def has_permission(self, request, view):
        if not site_sunucusu_mu(request):
            raise NotFound()
        return True