"""
Eczane ve Kiosk yonetim gorunumleri.

UoW ile yazma: tum CRUD perform_*() metotlari `UnitOfWork(user=request.user)`
icinden kaydeder; `olusturan/guncelleyen/surum` otomatik islenir.
"""
import re
import secrets

from django.conf import settings
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.audit.models import DenetimLogu, kayit_birak
from apps.core.uow import UnitOfWork

from .auth import (
    KioskAppKeyAuthentication,
    check_fleet_key,
    create_iot_token,
    is_timestamp_fresh,
    verify_provision_hmac,
)
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


MAC_RE = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$")


def _normalize_mac(raw: str) -> str:
    value = (raw or "").strip().upper().replace("-", ":")
    return value


class KioskBootstrapView(APIView):
    """POST /api/pharmacies/kiosks/bootstrap/

    Kiosk ilk aktivasyonunda cihaz kimligini ve IoT token'ini alir.

    Istek:
      Header  X-Kiosk-Key: <KIOSK_FLEET_KEY>
      Body    {
                "mac_adresi": "AA:BB:CC:DD:EE:FF",
                "timestamp":  "2026-06-04T10:00:00Z",   # ISO-8601 UTC
                "hmac":       "<HMAC-SHA256(MAC_UPPER + timestamp, KIOSK_PROVISIONING_SECRET)>"
              }

    Yanit:
      { "iot_token": "...", "kiosk_id": 1, "pharmacy_id": 1,
        "kiosk_adi": "...", "expires_in_days": 7 }
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        fleet_key = getattr(settings, "KIOSK_FLEET_KEY", "") or ""
        provisioning_secret = getattr(settings, "KIOSK_PROVISIONING_SECRET", "") or ""

        if not fleet_key or not provisioning_secret:
            return Response(
                {"detail": "Kiosk provision devre disi (sunucu ayarlari eksik)."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 1) Fleet key kontrolu
        if not check_fleet_key(request):
            return Response(
                {"detail": "Gecersiz veya eksik X-Kiosk-Key."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # 2) Body alanlari
        raw_mac = request.data.get("mac_adresi") or request.headers.get("X-Kiosk-MAC", "")
        mac = _normalize_mac(raw_mac)
        timestamp = (request.data.get("timestamp") or "").strip()
        received_hmac = (request.data.get("hmac") or "").strip()

        if not MAC_RE.match(mac):
            return Response({"detail": "Gecersiz MAC adresi."}, status=status.HTTP_400_BAD_REQUEST)

        if not timestamp or not received_hmac:
            return Response(
                {"detail": "timestamp ve hmac alanlari zorunludur."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3) Timestamp tazelik kontrolu (replay koruyu, +/- 5 dk)
        if not is_timestamp_fresh(timestamp):
            return Response(
                {"detail": "Timestamp gecersiz veya suresi dolmus (max +/-5 dk)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4) HMAC dogrulama
        if not verify_provision_hmac(mac, timestamp, received_hmac, provisioning_secret):
            return Response(
                {"detail": "HMAC imzasi dogrulanamadi."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # 5) MAC ile kiosk sorgulama
        kiosk = (
            Kiosk.objects
            .select_related("eczane")
            .filter(aktif=True, mac_adresi__iexact=mac)
            .first()
        )
        if not kiosk:
            return Response(
                {"detail": "Bu MAC adresi icin aktif kayitli kiosk bulunamadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 6) IoT token uret
        ttl_days: int = getattr(settings, "KIOSK_IOT_TOKEN_TTL_DAYS", 7)
        iot_token = create_iot_token(kiosk.pk, kiosk.eczane_id, mac)

        return Response(
            {
                "iot_token": iot_token,
                "kiosk_id": kiosk.pk,
                "pharmacy_id": kiosk.eczane_id,
                "kiosk_adi": kiosk.ad,
                "expires_in_days": ttl_days,
            },
            status=status.HTTP_200_OK,
        )


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

    queryset = Kiosk.objects.select_related("eczane__il", "eczane__ilce").all()
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

    @action(
        detail=False,
        methods=["get"],
        url_path="health",
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsSuperAdmin],
    )
    def health(self, request):
        """GET /api/pharmacies/kiosks/health/ — tüm kiosklarin online/offline durumu.

        Döner::
            [{ id, ad, mac_adresi, eczane_ad, is_online, son_goruldu,
               last_playlist_version, aktif }]
        """
        from django.utils import timezone as _tz
        import datetime as _dt
        threshold = _tz.now() - _dt.timedelta(minutes=5)
        kiosks = (
            Kiosk.objects
            .select_related("eczane")
            .filter(aktif=True)
            .order_by("eczane__ad", "ad")
        )
        data = [
            {
                "id": k.pk,
                "ad": k.ad,
                "mac_adresi": k.mac_adresi,
                "eczane_id": k.eczane_id,
                "eczane_ad": k.eczane.ad if k.eczane_id else None,
                "is_online": bool(k.son_goruldu and k.son_goruldu >= threshold),
                "son_goruldu": k.son_goruldu.isoformat() if k.son_goruldu else None,
                "last_playlist_version": k.last_playlist_version,
                "aktif": k.aktif,
            }
            for k in kiosks
        ]
        return Response(data)

