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

from .auth import KioskAppKeyAuthentication
from .models import Eczane, Kiosk, KioskEczaneAtama, KioskProvisioningRequest
from .permissions import IsKiosk, IsSuperAdmin
from .serializers import (
    EczaneSerializer,
    KioskProvisioningApproveSerializer,
    KioskProvisioningRejectSerializer,
    KioskProvisioningRequestSerializer,
    KioskSerializer,
    KioskTransferSerializer,
)


def _client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class _AnahtarYenileThrottle(UserRateThrottle):
    """SEC-008: regenerate_key endpoint'ine ozgu siki oran siniri."""

    scope = "admin_sensitive"


# ── Provisioning yardimcilari ─────────────────────────────────────────────────

_PROVISIONING_RETRY_AFTER = 30  # saniye


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

            # Eczanede kullanılan slot'ları kilitleyerek boş slot bul (1-31)
            taken = set(
                Kiosk.objects
                .select_for_update()
                .filter(eczane=eczane, eczane_kiosk_no__isnull=False)
                .values_list("eczane_kiosk_no", flat=True)
            )
            kiosk_no = next((n for n in range(1, 32) if n not in taken), None)
            if kiosk_no is None:
                return Response(
                    {"detail": "Bu eczanede maksimum kiosk sayısına (31) ulaşıldı."},
                    status=status.HTTP_409_CONFLICT,
                )

            # Yeni Kiosk olustur (UoW ile; olusturan/guncelleyen otomatik set edilir)
            new_kiosk = Kiosk(
                eczane=eczane,
                ad=kiosk_ad,
                mac_adresi=provision_req.mac_adresi.upper(),
                device_id=provision_req.device_id or None,
                uygulama_anahtari=secrets.token_urlsafe(48),
                aktif=True,
                eczane_kiosk_no=kiosk_no,
            )
            with UnitOfWork(user=request.user) as uow:
                uow.add(new_kiosk)
                uow.add(KioskEczaneAtama(
                    kiosk=new_kiosk, eczane=eczane, baslangic_zamani=now,
                    tasiyan_admin=request.user,
                ))

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

    queryset = Kiosk.objects.select_related("eczane__il", "eczane__ilce").prefetch_related("eczane_atamalari__eczane").all()
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
        with transaction.atomic(), UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
            uow.add(KioskEczaneAtama(
                kiosk=instance, eczane=instance.eczane,
                baslangic_zamani=timezone.now(), tasiyan_admin=self.request.user,
            ))
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

    @action(
        detail=True, methods=["post"], url_path="transfer",
        authentication_classes=[JWTAuthentication], permission_classes=[IsSuperAdmin],
    )
    def transfer(self, request, pk=None):
        payload = KioskTransferSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        target_id = payload.validated_data["eczane_id"]
        reason = payload.validated_data["tasima_nedeni"].strip()
        now = timezone.now()
        with transaction.atomic():
            kiosk = Kiosk.objects.select_for_update().select_related("eczane").get(pk=pk)
            if kiosk.eczane_id == target_id:
                return Response({"detail": "Kiosk zaten seçilen eczaneye bağlı."}, status=409)
            target = Eczane.objects.select_for_update().filter(pk=target_id, aktif=True).first()
            if target is None:
                return Response({"detail": "Hedef eczane bulunamadı veya pasif."}, status=400)
            current = KioskEczaneAtama.objects.select_for_update().filter(
                kiosk=kiosk, bitis_zamani__isnull=True
            ).first()
            if current is None:
                return Response({"detail": "Kioskun açık eczane ataması bulunamadı."}, status=409)
            taken = set(Kiosk.objects.select_for_update().filter(
                eczane=target, eczane_kiosk_no__isnull=False
            ).values_list("eczane_kiosk_no", flat=True))
            new_no = next((value for value in range(1, 32) if value not in taken), None)
            if new_no is None:
                return Response({"detail": "Hedef eczanede boş kiosk sırası yok."}, status=409)
            old_pharmacy = kiosk.eczane
            with UnitOfWork(user=request.user) as uow:
                current.bitis_zamani = now
                uow.update(current, update_fields=["bitis_zamani"])
                uow.add(KioskEczaneAtama(
                    kiosk=kiosk, eczane=target, baslangic_zamani=now,
                    tasima_nedeni=reason, tasiyan_admin=request.user,
                ))
                kiosk.eczane = target
                kiosk.eczane_kiosk_no = new_no
                uow.update(kiosk, update_fields=["eczane_id", "eczane_kiosk_no"])
            # UoW optimistic UPDATE kullandığı için Django post_save sinyali
            # otomatik tetiklenmez; mevcut invalidation receiver'ını aynı
            # old/new kapsam bilgisiyle çağır.
            from apps.campaigns.signals import _on_kiosk_save
            kiosk._old_eczane_id = old_pharmacy.id
            _on_kiosk_save(Kiosk, kiosk, created=False, update_fields={"eczane_id", "eczane_kiosk_no"})
        kayit_birak(
            eylem=DenetimLogu.Eylem.GUNCELLE, aktor=request.user, hedef=kiosk,
            ozet=f"Kiosk taşındı: {old_pharmacy.ad} -> {target.ad}", kiosk_mac=kiosk.mac_adresi,
            ip_adresi=_client_ip(request),
        )
        return Response(KioskSerializer(kiosk).data)

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
        url_path="reset-device-id",
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsSuperAdmin],
    )
    def reset_device_id(self, request, pk=None):
        """POST /api/pharmacies/kiosks/{id}/reset-device-id/ — device_id'yi NULL'a sifirlar.

        Kioskin SQLite DB'si sifirlandi veya farkli bir cihaza tasindiysa device_id
        uyusmazligi olusur. Bu endpoint eski device_id'yi siler; kiosk bir sonraki
        enrollDeviceId'de yeniden baglar.
        """
        kiosk: Kiosk = self.get_object()
        kiosk.device_id = None
        with UnitOfWork(user=request.user) as uow:
            uow.update(kiosk, update_fields=["device_id"])
        kayit_birak(
            eylem=DenetimLogu.Eylem.GUNCELLE,
            aktor=request.user,
            hedef=kiosk,
            ozet=f"Kiosk device_id sifirlandi: {kiosk.mac_adresi}",
            kiosk_mac=kiosk.mac_adresi,
            ip_adresi=_client_ip(request),
        )
        return Response({"status": "device_id_reset", "kiosk_id": kiosk.pk})

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

