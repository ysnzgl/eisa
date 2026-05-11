"""
Eczane ve Kiosk yonetim gorunumleri.

UoW ile yazma: tum CRUD perform_*() metotlari `UnitOfWork(user=request.user)`
icinden kaydeder; `olusturan/guncelleyen/surum` otomatik islenir.
"""
import secrets

from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.audit.models import DenetimLogu, kayit_birak
from apps.core.uow import UnitOfWork

from .auth import KioskAppKeyAuthentication
from .models import Eczane, Kiosk
from .permissions import IsKiosk, IsSuperAdmin
from .serializers import EczaneSerializer, KioskSerializer


def _client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class _AnahtarYenileThrottle(UserRateThrottle):
    """SEC-008: regenerate_key endpoint'ine ozgu siki oran siniri."""

    scope = "admin_sensitive"


class EczaneViewSet(viewsets.ModelViewSet):
    """Eczane CRUD. Listeleme/detay: tum auth; yazma: super admin (UoW)."""

    queryset = Eczane.objects.select_related("il", "ilce").all()
    serializer_class = EczaneSerializer
    authentication_classes = [JWTAuthentication]

    def get_queryset(self):
        qs = super().get_queryset().annotate(kiosk_sayisi=Count("kiosklar"))
        ilce_id = self.request.query_params.get("ilce")
        if ilce_id:
            qs = qs.filter(ilce_id=ilce_id)
        return qs

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsSuperAdmin()]

    def perform_create(self, serializer):
        instance = Eczane(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
        serializer.instance = instance
        kayit_birak(
            eylem=DenetimLogu.Eylem.OLUSTUR,
            aktor=self.request.user,
            hedef=instance,
            ozet=f"Eczane olusturuldu: {instance}",
            ip_adresi=_client_ip(self.request),
        )

    def perform_update(self, serializer):
        instance: Eczane = serializer.instance
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)
        kayit_birak(
            eylem=DenetimLogu.Eylem.GUNCELLE,
            aktor=self.request.user,
            hedef=instance,
            ozet=f"Eczane guncellendi: {instance}",
            ip_adresi=_client_ip(self.request),
        )

    def perform_destroy(self, instance):
        target_id = instance.pk
        repr_ = str(instance)
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)
        kayit_birak(
            eylem=DenetimLogu.Eylem.SIL,
            aktor=self.request.user,
            hedef_tipi="Eczane",
            hedef_id=target_id,
            ozet=f"Eczane silindi: {repr_}",
            ip_adresi=_client_ip(self.request),
        )


class KioskViewSet(viewsets.ModelViewSet):
    """Kiosk CRUD (super admin) + /me/ (kiosk) + /regenerate-key/ (admin)."""

    queryset = Kiosk.objects.select_related("eczane").all()
    serializer_class = KioskSerializer
    authentication_classes = [JWTAuthentication, KioskAppKeyAuthentication]

    def get_queryset(self):
        qs = super().get_queryset()
        eczane_id = self.request.query_params.get("eczane")
        if eczane_id:
            qs = qs.filter(eczane_id=eczane_id)
        return qs

    def get_permissions(self):
        if self.action == "me":
            return [IsKiosk()]
        return [IsSuperAdmin()]

    def perform_create(self, serializer):
        instance = Kiosk(
            uygulama_anahtari=secrets.token_urlsafe(48),
            **serializer.validated_data,
        )
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
        serializer.instance = instance
        kayit_birak(
            eylem=DenetimLogu.Eylem.OLUSTUR,
            aktor=self.request.user,
            hedef=instance,
            ozet=f"Kiosk olusturuldu: {instance.mac_adresi}",
            kiosk_mac=instance.mac_adresi,
            ip_adresi=_client_ip(self.request),
        )

    def perform_update(self, serializer):
        instance: Kiosk = serializer.instance
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)
        kayit_birak(
            eylem=DenetimLogu.Eylem.GUNCELLE,
            aktor=self.request.user,
            hedef=instance,
            ozet=f"Kiosk guncellendi: {instance.mac_adresi}",
            kiosk_mac=instance.mac_adresi,
            ip_adresi=_client_ip(self.request),
        )

    def perform_destroy(self, instance):
        target_id = instance.pk
        mac = instance.mac_adresi
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)
        kayit_birak(
            eylem=DenetimLogu.Eylem.SIL,
            aktor=self.request.user,
            hedef_tipi="Kiosk",
            hedef_id=target_id,
            ozet=f"Kiosk silindi: {mac}",
            kiosk_mac=mac,
            ip_adresi=_client_ip(self.request),
        )

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """GET /api/pharmacies/kiosks/me/ â€” App-Key ile kioskin kendi kaydi."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="regenerate-key",
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsSuperAdmin],
        throttle_classes=[_AnahtarYenileThrottle],
    )
    def regenerate_key(self, request, pk=None):
        """POST /api/pharmacies/kiosks/{id}/regenerate-key/ â€” yeni app_key uretir."""
        kiosk: Kiosk = self.get_object()
        kiosk.uygulama_anahtari = secrets.token_urlsafe(48)
        with UnitOfWork(user=request.user) as uow:
            uow.update(kiosk, update_fields=["uygulama_anahtari"])
        kayit_birak(
            eylem=DenetimLogu.Eylem.ANAHTAR_YENILE,
            aktor=request.user,
            hedef=kiosk,
            ozet=f"Kiosk app_key yenilendi: {kiosk.mac_adresi}",
            kiosk_mac=kiosk.mac_adresi,
            ip_adresi=_client_ip(request),
        )
        return Response({"uygulama_anahtari": kiosk.uygulama_anahtari}, status=status.HTTP_200_OK)

