"""
Eczane ve Kiosk yonetim gorunumleri.

UoW ile yazma: tum CRUD perform_*() metotlari `UnitOfWork(user=request.user)`
icinden kaydeder; `olusturan/guncelleyen/surum` otomatik islenir.
"""
import re
import secrets

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F
from django.utils import timezone
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
from .models import Eczane, Kiosk, KioskProvisioningRequest
from .permissions import IsKiosk, IsSuperAdmin
from .serializers import (
    EczaneSerializer,
    KioskProvisioningApproveSerializer,
    KioskProvisioningRejectSerializer,
    KioskProvisioningRequestSerializer,
    KioskSerializer,
)


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


# ── Provisioning yardimcilari ─────────────────────────────────────────────────

_PROVISIONING_RETRY_AFTER = 30  # saniye


def _bootstrap_credentials_ok(request) -> tuple[bool, str | None]:
    """
    Fleet key + body alanlarini dogrular.
    Basarisizsa (False, hata_mesaji) doner; hassas detay icermez.
    """
    fleet_key = getattr(settings, "KIOSK_FLEET_KEY", "") or ""
    provisioning_secret = getattr(settings, "KIOSK_PROVISIONING_SECRET", "") or ""

    if not fleet_key or not provisioning_secret:
        return False, "Kiosk provision devre disi (sunucu ayarlari eksik)."

    if not check_fleet_key(request):
        return False, None  # caller 401 donecek

    raw_mac = request.data.get("mac_adresi") or request.headers.get("X-Kiosk-MAC", "")
    mac = _normalize_mac(raw_mac)
    if not MAC_RE.match(mac):
        return False, "Gecersiz MAC adresi."

    timestamp = (request.data.get("timestamp") or "").strip()
    received_hmac = (request.data.get("hmac") or "").strip()
    if not timestamp or not received_hmac:
        return False, "timestamp ve hmac alanlari zorunludur."

    if not is_timestamp_fresh(timestamp):
        return False, "Timestamp gecersiz veya suresi dolmus (max +/-5 dk)."

    if not verify_provision_hmac(mac, timestamp, received_hmac, provisioning_secret):
        return False, None  # caller 401 donecek; hangi credential hatali oldugu belirtilmez

    return True, None


def _create_iot_token_for_kiosk(kiosk: Kiosk) -> dict:
    ttl_days: int = getattr(settings, "KIOSK_IOT_TOKEN_TTL_DAYS", 7)
    token = create_iot_token(kiosk.pk, kiosk.eczane_id, kiosk.mac_adresi)
    return {
        "iot_token": token,
        "kiosk_id": kiosk.pk,
        "pharmacy_id": kiosk.eczane_id,
        "kiosk_adi": kiosk.ad,
        "expires_in_days": ttl_days,
    }


class KioskBootstrapView(APIView):
    """POST /api/pharmacies/kiosks/bootstrap/

    Kiosk ilk aktivasyonunda cihaz kimligini ve IoT token'ini alir.
    Kayitli olmayan cihazlar icin onay-bekleyen kayit olusturur (202 Accepted).

    Istek:
      Header  X-Kiosk-Key: <KIOSK_FLEET_KEY>
      Body    {
                "mac_adresi": "AA:BB:CC:DD:EE:FF",
                "timestamp":  "2026-06-04T10:00:00Z",   # ISO-8601 UTC
                "hmac":       "<HMAC-SHA256(MAC_UPPER + timestamp, KIOSK_PROVISIONING_SECRET)>"
              }

    Yanitlar:
      200 — { "iot_token": "...", "kiosk_id": 1, "pharmacy_id": 1, ... }
            Kayitli ve aktif kiosk; IoT token verildi.
      202 — { "status": "PENDING", "registration_id": "uuid", ... }
            Yeni veya onay-bekleyen cihaz; admin onayi bekleniyor.
      403 — { "status": "REJECTED", "message": "..." }
            Admin tarafindan reddedilmis cihaz.
      401 — Gecersiz kimlik bilgisi (fleet key veya HMAC hatali).
      400 — Eksik/hatalı format.
      503 — Sunucu yapilandirmasi eksik.
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

        # 1) Fleet key kontrolu (hangi credential eksik oldugu response'ta belirtilmez)
        if not check_fleet_key(request):
            return Response(
                {"detail": "Kimlik dogrulanamadi."},
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

        # 4) HMAC dogrulama (SEC: hangi credential hatali oldugu belirtilmez)
        if not verify_provision_hmac(mac, timestamp, received_hmac, provisioning_secret):
            return Response(
                {"detail": "Kimlik dogrulanamadi."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # 5) Aktif kayitli kiosk var mi?
        kiosk = (
            Kiosk.objects
            .select_related("eczane")
            .filter(aktif=True, mac_adresi__iexact=mac)
            .first()
        )
        if kiosk:
            # Kayitli cihaz — mevcut provisioning akisina devam
            return Response(_create_iot_token_for_kiosk(kiosk), status=status.HTTP_200_OK)

        # 6) Provision talebi kontrol / olustur (kimlik dogrulamasi basarili gecirildi)
        now = timezone.now()
        hostname = (request.data.get("hostname") or "").strip()[:255]
        raw_metadata = request.data.get("device_metadata") or {}
        if isinstance(raw_metadata, dict):
            # SEC: credential/token iceriyorsa temizle
            device_metadata = {
                k: v for k, v in raw_metadata.items()
                if k not in ("iot_token", "token", "secret", "hmac", "authorization", "app_key")
            }
        else:
            device_metadata = {}

        provision_req = (
            KioskProvisioningRequest.objects
            .filter(mac_adresi__iexact=mac)
            .order_by("-olusturulma_tarihi")
            .first()
        )

        if provision_req:
            if provision_req.status == KioskProvisioningRequest.Status.APPROVED:
                # Onaylanmis: bagli kiosk varsa token ver
                linked_kiosk = provision_req.kiosk
                if linked_kiosk and linked_kiosk.aktif:
                    return Response(
                        _create_iot_token_for_kiosk(linked_kiosk),
                        status=status.HTTP_200_OK,
                    )
                # Kiosk silinmis veya pasif — PENDING'e geri don
                KioskProvisioningRequest.objects.filter(pk=provision_req.pk).update(
                    status=KioskProvisioningRequest.Status.PENDING,
                    last_seen_at=now,
                    request_count=F("request_count") + 1,
                )
                provision_req.refresh_from_db()
                return Response(
                    {
                        "status": "PENDING",
                        "registration_id": str(provision_req.id),
                        "message": "Cihaz kaydi yonetici onayi bekleniyor.",
                        "retry_after_seconds": _PROVISIONING_RETRY_AFTER,
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            if provision_req.status == KioskProvisioningRequest.Status.REJECTED:
                return Response(
                    {
                        "status": "REJECTED",
                        "message": "Cihaz kaydi reddedildi.",
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # PENDING: idempotent guncelleme
            KioskProvisioningRequest.objects.filter(pk=provision_req.pk).update(
                last_seen_at=now,
                request_count=F("request_count") + 1,
                hostname=hostname or provision_req.hostname,
                device_metadata=device_metadata or provision_req.device_metadata,
            )
            return Response(
                {
                    "status": "PENDING",
                    "registration_id": str(provision_req.id),
                    "message": "Cihaz kaydi yonetici onayi bekleniyor.",
                    "retry_after_seconds": _PROVISIONING_RETRY_AFTER,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        # Yeni cihaz — PENDING kayit olustur
        try:
            provision_req = KioskProvisioningRequest(
                mac_adresi=mac,
                hostname=hostname,
                device_metadata=device_metadata,
                status=KioskProvisioningRequest.Status.PENDING,
                last_seen_at=now,
                request_count=1,
            )
            provision_req.save()
        except Exception:
            # Ayni anda gelen es-zamanli istek zaten olusturmussa mevcut kaydı dondur
            provision_req = (
                KioskProvisioningRequest.objects
                .filter(mac_adresi__iexact=mac)
                .order_by("-olusturulma_tarihi")
                .first()
            )
            if provision_req:
                KioskProvisioningRequest.objects.filter(pk=provision_req.pk).update(
                    last_seen_at=now,
                    request_count=F("request_count") + 1,
                )
            else:
                return Response(
                    {"detail": "Provision talebi olusturulamadi, daha sonra tekrar deneyin."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        return Response(
            {
                "status": "PENDING",
                "registration_id": str(provision_req.id),
                "message": "Cihaz kaydi yonetici onayi bekleniyor.",
                "retry_after_seconds": _PROVISIONING_RETRY_AFTER,
            },
            status=status.HTTP_202_ACCEPTED,
        )


# ── Provisioning Admin Gorunumleri ────────────────────────────────────────────

class KioskProvisioningListView(APIView):
    """GET /api/pharmacies/kiosks/provisioning/

    Provision taleplerini listeler. Yalnizca SuperAdmin erisebilir.

    Filtreler (query param):
      status  — PENDING | APPROVED | REJECTED
      mac     — MAC adresi (iexact)
      hostname — Hostname (icontains)
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        qs = KioskProvisioningRequest.objects.select_related(
            "approved_by", "rejected_by", "kiosk"
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        mac_filter = request.query_params.get("mac")
        if mac_filter:
            qs = qs.filter(mac_adresi__iexact=mac_filter.strip())
        hostname_filter = request.query_params.get("hostname")
        if hostname_filter:
            qs = qs.filter(hostname__icontains=hostname_filter.strip())
        serializer = KioskProvisioningRequestSerializer(qs, many=True)
        return Response(serializer.data)


class KioskProvisioningDetailView(APIView):
    """GET /api/pharmacies/kiosks/provisioning/{id}/

    Provision talebi detayı. Yalnizca SuperAdmin erisebilir.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        try:
            obj = KioskProvisioningRequest.objects.select_related(
                "approved_by", "rejected_by", "kiosk"
            ).get(pk=pk)
        except KioskProvisioningRequest.DoesNotExist:
            return Response({"detail": "Bulunamadi."}, status=status.HTTP_404_NOT_FOUND)
        serializer = KioskProvisioningRequestSerializer(obj)
        return Response(serializer.data)


class KioskProvisioningApproveView(APIView):
    """POST /api/pharmacies/kiosks/provisioning/{id}/approve/

    Onay bekleyen cihazi bir eczaneye baglar ve gercek Kiosk kaydi olusturur.
    Transaction icinde: select_for_update + Kiosk olusturma + APPROVED guncelleme.

    Idempotent: Ayni kiosk ile zaten onaylanmissa mevcut sonucu doner.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        serializer = KioskProvisioningApproveSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        eczane_id = serializer.validated_data["eczane_id"]
        kiosk_ad = serializer.validated_data["ad"].strip()

        try:
            eczane = Eczane.objects.get(pk=eczane_id, aktif=True)
        except Eczane.DoesNotExist:
            return Response(
                {"detail": "Belirtilen eczane bulunamadi veya pasif."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        with transaction.atomic():
            # Row-level lock: ayni anda iki admin ayni talebe onay veremesin
            try:
                provision_req = KioskProvisioningRequest.objects.select_for_update().get(pk=pk)
            except KioskProvisioningRequest.DoesNotExist:
                return Response({"detail": "Provision talebi bulunamadi."}, status=status.HTTP_404_NOT_FOUND)

            # Idempotent: zaten ayni kiosk ile onaylanmissa basarili dondur
            if provision_req.status == KioskProvisioningRequest.Status.APPROVED:
                if provision_req.kiosk:
                    serializer_out = KioskProvisioningRequestSerializer(provision_req)
                    return Response(serializer_out.data, status=status.HTTP_200_OK)
                # Onaylanmis ama kiosk yok (silinmis) — yeniden onayla
            elif provision_req.status == KioskProvisioningRequest.Status.REJECTED:
                return Response(
                    {"detail": "Bu talep reddedilmis. Once talebi yeniden aktif hale getirin."},
                    status=status.HTTP_409_CONFLICT,
                )

            # Bu MAC ile zaten bir kiosk var mi?
            existing_kiosk = Kiosk.objects.filter(mac_adresi__iexact=provision_req.mac_adresi).first()
            if existing_kiosk:
                # MAC zaten farkli bir kiosk'ta kayitli — conflict
                return Response(
                    {"detail": "Bu MAC adresi zaten baska bir kiosk kaydinda mevcut."},
                    status=status.HTTP_409_CONFLICT,
                )

            # Yeni Kiosk olustur (UoW ile; olusturan/guncelleyen otomatik set edilir)
            new_kiosk = Kiosk(
                eczane=eczane,
                ad=kiosk_ad,
                mac_adresi=provision_req.mac_adresi.upper(),
                uygulama_anahtari=secrets.token_urlsafe(48),
                aktif=True,
            )
            with UnitOfWork(user=request.user) as uow:
                uow.add(new_kiosk)

            # Provision talebi: APPROVED
            provision_req.status = KioskProvisioningRequest.Status.APPROVED
            provision_req.kiosk = new_kiosk
            provision_req.approved_by = request.user
            provision_req.approved_at = now
            provision_req.guncellenme_tarihi = now
            provision_req.guncelleyen = request.user
            provision_req.surum = provision_req.surum + 1
            provision_req.save(update_fields=[
                "status", "kiosk", "approved_by", "approved_at",
                "guncellenme_tarihi", "guncelleyen", "surum",
            ])

        kayit_birak(
            eylem=DenetimLogu.Eylem.OLUSTUR,
            aktor=request.user,
            hedef=new_kiosk,
            ozet=f"Kiosk provision onaylandi: {provision_req.mac_adresi} -> Eczane: {eczane.ad}",
            kiosk_mac=provision_req.mac_adresi,
            ip_adresi=_client_ip(request),
        )

        provision_req.refresh_from_db()
        serializer_out = KioskProvisioningRequestSerializer(provision_req)
        return Response(serializer_out.data, status=status.HTTP_200_OK)


class KioskProvisioningRejectView(APIView):
    """POST /api/pharmacies/kiosks/provisioning/{id}/reject/

    Onay bekleyen cihazi reddeder. Yalnizca SuperAdmin.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def post(self, request, pk):
        serializer = KioskProvisioningRejectSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        rejection_reason = serializer.validated_data.get("rejection_reason", "").strip()

        try:
            provision_req = KioskProvisioningRequest.objects.get(pk=pk)
        except KioskProvisioningRequest.DoesNotExist:
            return Response({"detail": "Provision talebi bulunamadi."}, status=status.HTTP_404_NOT_FOUND)

        if provision_req.status == KioskProvisioningRequest.Status.APPROVED:
            return Response(
                {"detail": "Onaylanmis talep reddedilemez."},
                status=status.HTTP_409_CONFLICT,
            )

        now = timezone.now()
        provision_req.status = KioskProvisioningRequest.Status.REJECTED
        provision_req.rejected_by = request.user
        provision_req.rejected_at = now
        provision_req.rejection_reason = rejection_reason
        provision_req.guncellenme_tarihi = now
        provision_req.guncelleyen = request.user
        provision_req.surum = provision_req.surum + 1
        provision_req.save(update_fields=[
            "status", "rejected_by", "rejected_at", "rejection_reason",
            "guncellenme_tarihi", "guncelleyen", "surum",
        ])

        serializer_out = KioskProvisioningRequestSerializer(provision_req)
        return Response(serializer_out.data, status=status.HTTP_200_OK)


# ── Eczane & Kiosk CRUD Gorunumleri ─────────────────────────────────────────

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

