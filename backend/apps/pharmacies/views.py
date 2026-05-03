"""
Eczane ve kiosk yönetim görünümleri.
SuperAdmin: tam CRUD; Eczacı: sadece okuma; Kiosk: kendi bilgileri.
"""
import secrets

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.audit.models import AuditLog, record as audit_record

from .auth import KioskAppKeyAuthentication
from .models import Kiosk, Pharmacy
from .permissions import IsKiosk, IsSuperAdmin
from .serializers import KioskSerializer, PharmacySerializer


def _client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class PharmacyViewSet(viewsets.ModelViewSet):
    """
    Eczane CRUD endpoint'leri.
    Listeleme ve görüntüleme: tüm kimlik doğrulanmış kullanıcılar.
    Oluşturma / güncelleme / silme: sadece süper admin.
    """

    queryset = Pharmacy.objects.all().order_by("name")
    serializer_class = PharmacySerializer
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        """Okuma işlemlerine geniş erişim, yazma işlemlerine sadece süper admin."""
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [IsSuperAdmin()]

    def perform_create(self, serializer):
        instance = serializer.save()
        audit_record(
            action=AuditLog.Action.CREATE,
            actor=self.request.user,
            target=instance,
            summary=f"Pharmacy created: {instance}",
            ip_address=_client_ip(self.request),
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        audit_record(
            action=AuditLog.Action.UPDATE,
            actor=self.request.user,
            target=instance,
            summary=f"Pharmacy updated: {instance}",
            ip_address=_client_ip(self.request),
        )

    def perform_destroy(self, instance):
        target_id = instance.pk
        target_repr = str(instance)
        instance.delete()
        audit_record(
            action=AuditLog.Action.DELETE,
            actor=self.request.user,
            target_type="Pharmacy",
            target_id=target_id,
            summary=f"Pharmacy deleted: {target_repr}",
            ip_address=_client_ip(self.request),
        )


class KioskViewSet(viewsets.ModelViewSet):
    """
    Kiosk CRUD endpoint'leri (süper admin).
    /me/ — Kioskin App-Key ile kendi bilgilerine erişmesi için özel endpoint.
    /{id}/regenerate-key/ — Yeni app_key üretir (süper admin).
    """

    queryset = Kiosk.objects.select_related("pharmacy").all().order_by("id")
    serializer_class = KioskSerializer
    # Hem JWT (admin) hem App-Key (kiosk) desteklenir
    authentication_classes = [JWTAuthentication, KioskAppKeyAuthentication]

    def get_permissions(self):
        """me endpoint'i kiosk'a açık; diğer tüm işlemler süper admin gerektirir."""
        if self.action == "me":
            return [IsKiosk()]
        return [IsSuperAdmin()]

    def perform_create(self, serializer):
        """Yeni kiosk kaydederken kriptografik olarak güvenli benzersiz app_key üret."""
        app_key = secrets.token_urlsafe(48)
        instance = serializer.save(app_key=app_key)
        audit_record(
            action=AuditLog.Action.CREATE,
            actor=self.request.user,
            target=instance,
            summary=f"Kiosk created: {instance.mac_address}",
            kiosk_mac=instance.mac_address,
            ip_address=_client_ip(self.request),
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        audit_record(
            action=AuditLog.Action.UPDATE,
            actor=self.request.user,
            target=instance,
            summary=f"Kiosk updated: {instance.mac_address}",
            kiosk_mac=instance.mac_address,
            ip_address=_client_ip(self.request),
        )

    def perform_destroy(self, instance):
        target_id = instance.pk
        mac = instance.mac_address
        instance.delete()
        audit_record(
            action=AuditLog.Action.DELETE,
            actor=self.request.user,
            target_type="Kiosk",
            target_id=target_id,
            summary=f"Kiosk deleted: {mac}",
            kiosk_mac=mac,
            ip_address=_client_ip(self.request),
        )

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """
        GET /api/pharmacies/kiosks/me/
        App-Key ile doğrulanmış kioskin kendi kayıt bilgilerini döner.
        """
        # KioskAppKeyAuthentication'dan gelen request.user doğrudan Kiosk nesnesidir
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="regenerate-key",
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsSuperAdmin],
    )
    def regenerate_key(self, request, pk=None):
        """
        POST /api/pharmacies/kiosks/{id}/regenerate-key/
        Mevcut app_key'i geçersiz kılarak yeni bir kriptografik anahtar üretir.
        """
        kiosk = self.get_object()
        kiosk.app_key = secrets.token_urlsafe(48)
        kiosk.save(update_fields=["app_key"])
        audit_record(
            action=AuditLog.Action.REGENERATE_KEY,
            actor=request.user,
            target=kiosk,
            summary=f"Kiosk app_key regenerated: {kiosk.mac_address}",
            kiosk_mac=kiosk.mac_address,
            ip_address=_client_ip(request),
        )
        return Response({"app_key": kiosk.app_key}, status=status.HTTP_200_OK)
