"""Abonelik API view'leri.

Yetkiler:
  Sözleşme / Cihaz planı / Fatura yönetimi : IsSuperAdmin
  Kendi hesabı / faturaları / ödeme        : IsEczaci (eczane izolasyonu)
"""
from __future__ import annotations

import logging
from decimal import Decimal

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.uow import UnitOfWork
from apps.pharmacies.permissions import IsEczaci, IsSuperAdmin
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from . import services
from .models import CihazOdemePlani, Fatura, FiyatTanimi, Odeme, Sozlesme, SozlesmeTalebi
from .serializers import (
    CihazOdemePlaniSerializer,
    FaturaSerializer,
    FiyatTanimiSerializer,
    OdemeSerializer,
    OdemeYapSerializer,
    SozlesmeSerializer,
    SozlesmeTalebiCreateSerializer,
    SozlesmeTalebiSerializer,
    SozlesmeUzatmaSerializer,
    SozlesmeUzatSerializer,
    TalepKararSerializer,
)

logger = logging.getLogger(__name__)


# ── Admin: Sözleşme yönetimi ────────────────────────────────────────────────

class SozlesmeViewSet(viewsets.ModelViewSet):
    """SuperAdmin sözleşme CRUD + cihaz planı ataması."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = SozlesmeSerializer

    def get_queryset(self):
        qs = (
            Sozlesme.objects.select_related("eczane")
            .prefetch_related("cihaz_plani")
            .all()
        )
        eczane_id = self.request.query_params.get("eczane")
        if eczane_id:
            qs = qs.filter(eczane_id=eczane_id)
        durum = self.request.query_params.get("durum")
        if durum:
            qs = qs.filter(durum=durum)
        return qs

    def perform_create(self, serializer):
        with UnitOfWork(user=self.request.user) as uow:
            instance = Sozlesme(**serializer.validated_data)
            uow.add(instance)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = serializer.instance
        for field, value in serializer.validated_data.items():
            setattr(instance, field, value)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)

    @action(detail=True, methods=["put"], url_path="cihaz-plani")
    def cihaz_plani(self, request, pk=None):
        """Sözleşmeye cihaz ödeme planı ekler veya günceller (upsert)."""
        sozlesme = self.get_object()
        plan = getattr(sozlesme, "cihaz_plani", None)
        serializer = CihazOdemePlaniSerializer(instance=plan, data=request.data, partial=plan is not None)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with UnitOfWork(user=request.user) as uow:
            if plan is None:
                plan = CihazOdemePlani(sozlesme=sozlesme, **data)
                uow.add(plan)
            else:
                for field, value in data.items():
                    setattr(plan, field, value)
                uow.update(plan)
        return Response(CihazOdemePlaniSerializer(plan).data,
                        status=status.HTTP_200_OK if sozlesme else status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="uzat")
    def uzat(self, request, pk=None):
        """Sözleşmeyi uzatır (standart: ay, demo: gün). Tarihçeye kaydeder."""
        sozlesme = self.get_object()
        body = SozlesmeUzatSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            services.uzat_sozlesme(
                sozlesme,
                ek_ay=body.validated_data.get("ek_ay"),
                ek_gun=body.validated_data.get("ek_gun"),
                neden=body.validated_data.get("neden", ""),
                user=request.user,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        sozlesme.refresh_from_db()
        return Response(SozlesmeSerializer(sozlesme).data)

    @action(detail=True, methods=["post"], url_path="iptal")
    def iptal(self, request, pk=None):
        """Sözleşmeyi iptal eder ve tarihçeye satır ekler."""
        sozlesme = self.get_object()
        neden = (request.data or {}).get("neden", "")
        try:
            services.iptal_sozlesme(sozlesme, neden=neden, user=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        sozlesme.refresh_from_db()
        return Response(SozlesmeSerializer(sozlesme).data)

    @action(detail=True, methods=["get"], url_path="gecmis")
    def gecmis(self, request, pk=None):
        """Sözleşmenin uzatma/iptal tarihçesi + aynı eczanenin sözleşme zinciri."""
        sozlesme = self.get_object()
        uzatmalar = sozlesme.uzatmalar.select_related("olusturan").all()
        eczane_sozlesmeleri = (
            Sozlesme.objects.filter(eczane_id=sozlesme.eczane_id)
            .select_related("eczane").order_by("-baslangic_tarihi", "-id")
        )
        return Response({
            "uzatmalar": SozlesmeUzatmaSerializer(uzatmalar, many=True).data,
            "sozlesmeler": SozlesmeSerializer(eczane_sozlesmeleri, many=True).data,
        })


# ── Admin: Fatura yönetimi ──────────────────────────────────────────────────

class FaturaViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """SuperAdmin tüm faturaları görür; manuel tahsilat işaretleyebilir."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = FaturaSerializer

    def get_queryset(self):
        qs = Fatura.objects.select_related("eczane").all()
        eczane_id = self.request.query_params.get("eczane")
        if eczane_id:
            qs = qs.filter(eczane_id=eczane_id)
        durum = self.request.query_params.get("durum")
        if durum:
            qs = qs.filter(durum=durum)
        return qs

    @action(detail=True, methods=["post"], url_path="ode")
    def ode(self, request, pk=None):
        """Faturayı manuel olarak ödenmiş işaretle (mock tahsilat)."""
        fatura = self.get_object()
        body = OdemeYapSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            odeme = services.ode_fatura(
                fatura, yontem=body.validated_data["yontem"], user=request.user
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OdemeSerializer(odeme).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="faturalandir")
    def faturalandir(self, request):
        """Günlük faturalandırma döngüsünü elle tetikler (idempotent).

        Kullanım bedeli + cihaz taksiti + cihaz kira faturalarını üretir ve
        gecikmiş faturaları işaretler. Admin, zamanlayıcıyı beklemeden sonucu görür.
        """
        kullanim = services.faturala_kullanim_bedeli()
        cihaz = services.faturala_cihaz_taksit()
        kira = services.faturala_cihaz_kira()
        gecikmis = services.guncelle_gecikmis_faturalar()
        return Response({
            "kullanim_bedeli": kullanim,
            "cihaz_taksit": cihaz,
            "cihaz_kira": kira,
            "gecikmis": gecikmis,
            "toplam_yeni": kullanim + cihaz + kira,
        })


# ── Admin: Fiyat tanımları (parametre) ────────────────────────────────

class FiyatTanimiViewSet(viewsets.ModelViewSet):
    """SuperAdmin fiyat tanımı (abonelik + cihaz kira bedeli) yönetimi, tarihçeli."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = FiyatTanimiSerializer
    queryset = FiyatTanimi.objects.all()

    def perform_create(self, serializer):
        with UnitOfWork(user=self.request.user) as uow:
            instance = FiyatTanimi(**serializer.validated_data)
            uow.add(instance)
        serializer.instance = instance

    @action(detail=False, methods=["get"], url_path="aktif")
    def aktif(self, request):
        """Bugün geçerli fiyat tanımını döner (yoksa null)."""
        fiyat = services.aktif_fiyat()
        return Response(FiyatTanimiSerializer(fiyat).data if fiyat else None)


# ── Eczacı: Kendi hesabı ────────────────────────────────────────────────────

class HesabimView(APIView):
    """GET /api/abonelik/hesabim/ — eczacının sözleşme + cari özeti."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def get(self, request):
        eczane_id = getattr(request.user, "eczane_id", None)
        if not eczane_id:
            return Response({"detail": "Kullanıcıya eczane atanmamış."},
                            status=status.HTTP_400_BAD_REQUEST)

        sozlesme = (
            Sozlesme.objects.filter(eczane_id=eczane_id)
            .select_related("eczane").prefetch_related("cihaz_plani")
            .order_by("-baslangic_tarihi").first()
        )
        acik_faturalar = Fatura.objects.filter(
            eczane_id=eczane_id,
            durum__in=(Fatura.Durum.BEKLIYOR, Fatura.Durum.GECIKTI),
        )
        toplam_borc = sum((f.tutar for f in acik_faturalar), start=Decimal("0.00"))
        erisim_kapali = services.eczane_erisim_kapali(eczane_id)
        demo = services.eczane_demo_modunda(eczane_id)
        kisitli, kisit_nedeni = services.panel_kisitli(eczane_id)

        return Response({
            "demo": demo,
            "panel_kisitli": kisitli,
            "kisit_nedeni": kisit_nedeni,
            "sozlesme": SozlesmeSerializer(sozlesme).data if sozlesme else None,
            "acik_fatura_sayisi": acik_faturalar.count(),
            "toplam_borc": str(toplam_borc),
            "erisim_kapali": erisim_kapali,
            "grace_gun": services.GRACE_DAYS,
        })


class FaturalarimView(APIView):
    """GET /api/abonelik/faturalarim/ — eczacının kendi faturaları."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def get(self, request):
        eczane_id = getattr(request.user, "eczane_id", None)
        if not eczane_id:
            return Response([], status=status.HTTP_200_OK)
        qs = Fatura.objects.filter(eczane_id=eczane_id).select_related("eczane")
        durum = request.query_params.get("durum")
        if durum:
            qs = qs.filter(durum=durum)
        return Response(FaturaSerializer(qs, many=True).data)


class FaturaOdeView(APIView):
    """POST /api/abonelik/faturalarim/{id}/ode/ — eczacı kendi faturasını öder (mock)."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def post(self, request, pk):
        eczane_id = getattr(request.user, "eczane_id", None)
        fatura = Fatura.objects.filter(pk=pk, eczane_id=eczane_id).first()
        if fatura is None:
            return Response({"detail": "Fatura bulunamadı."},
                            status=status.HTTP_404_NOT_FOUND)
        body = OdemeYapSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            odeme = services.ode_fatura(
                fatura, yontem=body.validated_data["yontem"], user=request.user
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OdemeSerializer(odeme).data, status=status.HTTP_201_CREATED)


class OdemelerimView(APIView):
    """GET /api/abonelik/odemelerim/ — eczacının ödeme geçmişi."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def get(self, request):
        eczane_id = getattr(request.user, "eczane_id", None)
        if not eczane_id:
            return Response([], status=status.HTTP_200_OK)
        qs = Odeme.objects.filter(fatura__eczane_id=eczane_id).select_related("fatura", "fatura__eczane")
        return Response(OdemeSerializer(qs, many=True).data)


class HareketlerimView(APIView):
    """GET /api/abonelik/hareketlerim/ — eczacının sözleşme hareketleri (tarihçe)."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def get(self, request):
        eczane_id = getattr(request.user, "eczane_id", None)
        if not eczane_id:
            return Response([], status=status.HTTP_200_OK)
        return Response(services.sozlesme_hareketleri(eczane_id))


class TaleplerimView(APIView):
    """GET/POST /api/abonelik/taleplerim/ — eczacı kendi sözleşme talepleri."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def get(self, request):
        eczane_id = getattr(request.user, "eczane_id", None)
        if not eczane_id:
            return Response([], status=status.HTTP_200_OK)
        qs = SozlesmeTalebi.objects.filter(eczane_id=eczane_id).select_related("eczane")
        return Response(SozlesmeTalebiSerializer(qs, many=True).data)

    def post(self, request):
        eczane_id = getattr(request.user, "eczane_id", None)
        if not eczane_id:
            return Response({"detail": "Kullanıcıya eczane atanmamış."},
                            status=status.HTTP_400_BAD_REQUEST)
        ser = SozlesmeTalebiCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        hedef = data.get("hedef_sozlesme")
        if hedef is not None and hedef.eczane_id != eczane_id:
            return Response({"detail": "Sözleşme bu eczaneye ait değil."},
                            status=status.HTTP_403_FORBIDDEN)
        with UnitOfWork(user=request.user) as uow:
            talep = SozlesmeTalebi(eczane_id=eczane_id, **data)
            uow.add(talep)
        return Response(SozlesmeTalebiSerializer(talep).data, status=status.HTTP_201_CREATED)


# ── Admin: Sözleşme talepleri ────────────────────────────────────────────────

class SozlesmeTalebiViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """SuperAdmin sözleşme taleplerini görür ve sonuçlandırır."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = SozlesmeTalebiSerializer

    def get_queryset(self):
        qs = SozlesmeTalebi.objects.select_related("eczane").all()
        eczane_id = self.request.query_params.get("eczane")
        if eczane_id:
            qs = qs.filter(eczane_id=eczane_id)
        durum = self.request.query_params.get("durum")
        if durum:
            qs = qs.filter(durum=durum)
        return qs

    @action(detail=True, methods=["post"], url_path="karar")
    def karar(self, request, pk=None):
        talep = self.get_object()
        body = TalepKararSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            services.karar_ver_talep(
                talep, onayla=body.validated_data["onayla"],
                red_nedeni=body.validated_data.get("red_nedeni", ""),
                user=request.user,
                detail_data={
                    "istenen_tur": body.validated_data.get("istenen_tur"),
                    "istenen_tip_ay": body.validated_data.get("istenen_tip_ay"),
                    "istenen_demo_gun": body.validated_data.get("istenen_demo_gun"),
                    "ek_ay": body.validated_data.get("ek_ay"),
                    "ek_gun": body.validated_data.get("ek_gun"),
                    "aciklama": body.validated_data.get("aciklama", ""),
                    "baslangic_tarihi": body.validated_data.get("baslangic_tarihi"),
                    "oteleme_ay": body.validated_data.get("oteleme_ay"),
                    "aylik_kullanim_bedeli": body.validated_data.get("aylik_kullanim_bedeli"),
                    "cihaz_durumu": body.validated_data.get("cihaz_durumu"),
                    "cihaz_kira_bedeli": body.validated_data.get("cihaz_kira_bedeli"),
                    "pesin_fiyat": body.validated_data.get("pesin_fiyat"),
                    "vade_farki_orani": body.validated_data.get("vade_farki_orani"),
                    "taksit_sayisi": body.validated_data.get("taksit_sayisi"),
                    "cihaz_baslangic_tarihi": body.validated_data.get("cihaz_baslangic_tarihi"),
                    "notlar": body.validated_data.get("notlar", ""),
                },
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        talep.refresh_from_db()
        return Response(SozlesmeTalebiSerializer(talep).data)

    @action(detail=False, methods=["get"], url_path="bekleyen-sayisi")
    def bekleyen_sayisi(self, request):
        sayi = SozlesmeTalebi.objects.filter(durum=SozlesmeTalebi.Durum.BEKLIYOR).count()
        return Response({"sayi": sayi})


class OdemelerView(mixins.ListModelMixin, viewsets.GenericViewSet):
    """SuperAdmin ödeme geçmişi (tarihçe)."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = OdemeSerializer

    def get_queryset(self):
        qs = Odeme.objects.select_related("fatura", "fatura__eczane").all()
        eczane_id = self.request.query_params.get("eczane")
        if eczane_id:
            qs = qs.filter(fatura__eczane_id=eczane_id)
        return qs
