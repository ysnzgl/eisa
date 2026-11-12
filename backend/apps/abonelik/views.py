"""Abonelik API view'leri.

Yetkiler:
  Sözleşme / Cihaz planı / Fatura yönetimi : IsSuperAdmin
  Kendi hesabı / faturaları / ödeme        : IsEczaci (eczane izolasyonu)
"""
from __future__ import annotations

import io
import logging
from decimal import Decimal

from django.utils import timezone
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, parsers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.uow import UnitOfWork
from apps.pharmacies.permissions import IsEczaci, IsSuperAdmin, IsSuperAdminOrEczaci
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from . import services
from .models import CihazOdemePlani, Fatura, FiyatTanimi, Odeme, Sozlesme, SozlesmeTalebi
from .serializers import (
    CihazOdemePlaniSerializer,
    FaturaSerializer,
    FaturaDuzeltSerializer,
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


def _new_wet_contract_notice(sozlesme, kind="EK1"):
    if sozlesme.sozlesme_surumu == "2026-EK1":
        from .contract_docx import ContractTemplateError, contract_preview_html
        from rest_framework.exceptions import ValidationError
        try:
            rendered, missing = contract_preview_html(sozlesme, kind)
        except ContractTemplateError as exc:
            raise ValidationError({"detail": str(exc)})
        return {"html": rendered, "dondurulmus": False, "belge_seti": "EK1_EK2",
                "belge_turu": kind, "eksik_alanlar": missing}
    return None


def _generated_contract_response(sozlesme, kind):
    from .contract_docx import ContractTemplateError, generate_contract_docx
    try:
        content, fields = generate_contract_docx(sozlesme, kind)
    except ContractTemplateError as exc:
        return Response({"detail": str(exc)}, status=400)
    response = FileResponse(io.BytesIO(content), as_attachment=True,
        filename=f"sozlesme-{sozlesme.pk}-{kind.lower()}.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    response["X-Eisa-Missing-Field-Count"] = str(len(fields))
    return response


# ── Admin: Sözleşme yönetimi ────────────────────────────────────────────────

class SozlesmeViewSet(viewsets.ModelViewSet):
    """SuperAdmin sözleşme CRUD + cihaz planı ataması."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
    serializer_class = SozlesmeSerializer

    def get_queryset(self):
        qs = (
            Sozlesme.objects.select_related("eczane")
            .prefetch_related("cihaz_planlari")
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

    def create(self, request, *args, **kwargs):
        """Sözleşmeyi ve (varsa) cihaz planlarını tek atomik işlemde kaydeder.

        Gövdeye eklenen `cihaz_planlari` listesi sözleşmeyle aynı transaction'da
        yazılır; biri başarısız olursa hiçbiri kaydedilmez (ya hep ya hiç).
        """
        data = request.data.copy()
        planlar = data.pop("cihaz_planlari", None)
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.instance = services.sozlesme_olustur(
            serializer.validated_data, planlar=planlar, user=request.user,
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def _kaydet_cihaz_planlari(self, sozlesme, planlar):
        services.kaydet_cihaz_planlari(sozlesme, planlar, user=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        for field, value in serializer.validated_data.items():
            setattr(instance, field, value)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)

    def update(self, request, *args, **kwargs):
        from django.db import transaction
        data = request.data.copy()
        planlar = data.pop("cihaz_planlari", None)
        if planlar is not None and not isinstance(planlar, list):
            return Response({"cihaz_planlari": "Liste bekleniyor."}, status=400)
        with transaction.atomic():
            instance = get_object_or_404(self.get_queryset().select_for_update(), pk=kwargs["pk"])
            serializer = self.get_serializer(instance, data=data, partial=kwargs.get("partial", False))
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            if planlar is not None:
                self._kaydet_cihaz_planlari(instance, planlar)
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    @action(detail=True, methods=["put"], url_path="cihaz-planlari")
    def cihaz_planlari_guncelle(self, request, pk=None):
        """Sözleşmenin cihaz planlarını toplu günceller (replace-all).

        Gövde: [{id?, adet, pesin_fiyat, vade_farki_orani, taksit_sayisi,
                  baslangic_tarihi, cihaz_kdv_orani}, ...]
        """
        from django.db import transaction

        sozlesme = self.get_object()
        if not isinstance(request.data, list):
            return Response({"detail": "Liste bekleniyor."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            self._kaydet_cihaz_planlari(sozlesme, request.data)

        sozlesme._prefetched_objects_cache = {}

        qs = CihazOdemePlani.objects.filter(sozlesme=sozlesme)
        return Response(CihazOdemePlaniSerializer(qs, many=True).data)

    @action(detail=True, methods=["put"], url_path="cihaz-plani")
    def cihaz_plani(self, request, pk=None):
        """Geriye dönük uyumluluk: tek cihaz planı upsert (eskiden kullanılıyordu)."""
        return self.cihaz_planlari_guncelle(
            request._request if hasattr(request, "_request") else request, pk=pk
        )

    @action(detail=True, methods=["get"], url_path="metin")
    def metin(self, request, pk=None):
        """Sözleşmenin tam metni (HTML). Onaylıysa dondurulmuş metin, değilse canlı önizleme."""
        from .contract_template import onay_blogu_html, render_sozlesme_html

        sozlesme = self.get_object()
        if sozlesme.onayli_sozlesme_metni:
            return Response({"html": sozlesme.onayli_sozlesme_metni, "dondurulmus": True})
        notice = _new_wet_contract_notice(sozlesme, (request.query_params.get("belge_turu") or "EK1").upper())
        if notice:
            return Response(notice)
        html = render_sozlesme_html(sozlesme) + onay_blogu_html(sozlesme)
        return Response({"html": html, "dondurulmus": False})

    @action(detail=True, methods=["get"], url_path="belge-veri-kontrol")
    def belge_veri_kontrol(self, request, pk=None):
        """Word çıktısında elle tamamlanması gereken alanları bildirir."""
        from .contract_docx import missing_fields

        sozlesme = self.get_object()
        if sozlesme.sozlesme_surumu != "2026-EK1":
            return Response({"detail": "Eski sözleşme yeni belge şablonuyla oluşturulamaz."}, status=400)
        kind = (request.query_params.get("belge_turu") or "EK1").upper()
        if kind not in ("EK1", "EK2"):
            return Response({"detail": "belge_turu EK1 veya EK2 olmalıdır."}, status=400)
        fields = missing_fields(sozlesme, kind)
        return Response({"belge_turu": kind, "eksik_alanlar": fields, "hazir": not fields})

    @action(detail=True, methods=["get"], url_path="belge-olustur")
    def belge_olustur(self, request, pk=None):
        """Onaylı Word şablonundan doldurulmuş Ek-1 veya Ek-2 üretir."""
        sozlesme = self.get_object()
        kind = (request.query_params.get("belge_turu") or "EK1").upper()
        return _generated_contract_response(sozlesme, kind)

    @action(detail=True, methods=["post"], url_path="islak-imza-yukle",
            parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def islak_imza_yukle(self, request, pk=None):
        """Ana sözleşme/Ek-1 veya Ek-2 ıslak imzalı belgesini ayrı saklar."""
        sozlesme = self.get_object()
        belge = request.FILES.get("belge")
        belge_turu = (request.data.get("belge_turu") or "SOZLESME_EK1").upper()
        if belge_turu not in ("SOZLESME_EK1", "EK2"):
            return Response({"detail": "belge_turu SOZLESME_EK1 veya EK2 olmalıdır."}, status=status.HTTP_400_BAD_REQUEST)
        if not belge:
            return Response({"detail": "Dosya gerekli (alan adı: belge)."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            from apps.core.services.storage_service import StorageService
            storage = StorageService()
            object_key = storage.upload_file(belge, prefix=f"sozlesmeler/{pk}/{belge_turu.lower()}")
        except Exception as exc:
            logger.exception("Islak imza yükleme hatası")
            return Response({"detail": f"Depolama hatası: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        sozlesme.imza_tipi = Sozlesme.ImzaTipi.ISLAK
        now = timezone.now()
        if belge_turu == "EK2":
            sozlesme.ek2_islak_imza_url = object_key
            sozlesme.ek2_islak_yukleme_tarihi = now
            fields = ["ek2_islak_imza_url", "ek2_islak_yukleme_tarihi", "imza_tipi"]
        else:
            sozlesme.islak_imza_url = object_key
            sozlesme.islak_yukleme_tarihi = now
            fields = ["islak_imza_url", "islak_yukleme_tarihi", "imza_tipi"]
        # Dosya yükleme zamanı dijital onay veya gerçek imza zamanı değildir.
        sozlesme.save(update_fields=fields)
        return Response({"object_key": object_key, "belge_turu": belge_turu,
                         "imza_tipi": sozlesme.imza_tipi})

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
        qs = Fatura.objects.select_related("eczane").prefetch_related("kalemler", "odemeler", "islemler__olusturan").all()
        eczane_id = self.request.query_params.get("eczane")
        if eczane_id:
            qs = qs.filter(eczane_id=eczane_id)
        durum = self.request.query_params.get("durum")
        if durum:
            qs = qs.filter(durum=durum)
        if self.request.query_params.get("unpaid_only") in ("1", "true", "yes", "on"):
            qs = qs.filter(durum__in=(Fatura.Durum.BEKLIYOR, Fatura.Durum.GECIKTI))
        tarih_baslangic = self.request.query_params.get("tarih_baslangic")
        if tarih_baslangic:
            qs = qs.filter(vade_tarihi__gte=tarih_baslangic)
        tarih_bitis = self.request.query_params.get("tarih_bitis")
        if tarih_bitis:
            qs = qs.filter(vade_tarihi__lte=tarih_bitis)
        return qs

    @action(detail=True, methods=["post"], url_path="ode")
    def ode(self, request, pk=None):
        """Faturayı manuel olarak ödenmiş işaretle (mock tahsilat)."""
        fatura = self.get_object()
        body = OdemeYapSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            odeme = services.ode_fatura(
                fatura, yontem=body.validated_data["yontem"],
                aciklama=body.validated_data.get("aciklama", ""),
                user=request.user
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(OdemeSerializer(odeme).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="faturalandir")
    def faturalandir(self, request):
        """Abonelik ve cihaz faturalarını ayrı ayrı üretir."""
        ayri = services.faturala_ayri()
        gecikmis = services.guncelle_gecikmis_faturalar()
        return Response({
            "ayri_fatura": ayri,
            "gecikmis": gecikmis,
            "toplam_yeni": ayri,
        })

    @action(detail=True, methods=["get"], url_path="yeniden-olustur-onizleme")
    def yeniden_olustur_onizleme(self, request, pk=None):
        from .invoice_corrections import preview
        try:
            return Response(preview(self.get_object()))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def _duzelt(self, request, islem):
        from .invoice_corrections import correct
        fatura = self.get_object()
        body = FaturaDuzeltSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        try:
            result = correct(fatura.pk, islem=islem, user=request.user, **body.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(FaturaSerializer(result).data)

    @action(detail=True, methods=["post"], url_path="iptal")
    def iptal(self, request, pk=None):
        return self._duzelt(request, "IPTAL")

    @action(detail=True, methods=["post"], url_path="yeniden-olustur")
    def yeniden_olustur(self, request, pk=None):
        return self._duzelt(request, "YENIDEN_OLUSTUR")

    @action(detail=True, methods=["post"], url_path="odemeyi-geri-al")
    def odemeyi_geri_al(self, request, pk=None):
        return self._duzelt(request, "ODEME_GERI_AL")


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
            .select_related("eczane").prefetch_related("cihaz_planlari")
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
            # Islak imzalı sözleşmelerde dijital onay istenmez.
            "onay_gerekli": bool(sozlesme and sozlesme.onay_gerekli),
            "ceza_tutari": str(sozlesme.iptal_ceza_tutari) if sozlesme else "0.00",
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
                fatura, yontem=body.validated_data["yontem"],
                aciklama=body.validated_data.get("aciklama", ""),
                user=request.user
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


class SozlesmeOnaylaView(APIView):
    """POST /api/abonelik/sozlesmelerim/{pk}/onayla/ — eczacı dijital onayı."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def post(self, request, pk):
        eczane_id = getattr(request.user, "eczane_id", None)
        sozlesme = Sozlesme.objects.filter(pk=pk, eczane_id=eczane_id).first()
        if sozlesme is None:
            return Response({"detail": "Sözleşme bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        if not sozlesme.onay_gerekli:
            return Response(SozlesmeSerializer(sozlesme).data)  # idempotent
        ip = request.META.get("REMOTE_ADDR", "")
        try:
            services.sozlesme_onayla(sozlesme, ip_address=ip, user=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        sozlesme.refresh_from_db()
        return Response(SozlesmeSerializer(sozlesme).data)


class SozlesmeMetniView(APIView):
    """GET /api/abonelik/sozlesmelerim/{pk}/metin/ — eczacının kendi sözleşme metni."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def get(self, request, pk):
        from .contract_template import onay_blogu_html, render_sozlesme_html

        eczane_id = getattr(request.user, "eczane_id", None)
        sozlesme = Sozlesme.objects.filter(pk=pk, eczane_id=eczane_id).first()
        if sozlesme is None:
            return Response({"detail": "Sözleşme bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        if sozlesme.onayli_sozlesme_metni:
            return Response({"html": sozlesme.onayli_sozlesme_metni, "dondurulmus": True})
        notice = _new_wet_contract_notice(sozlesme, (request.query_params.get("belge_turu") or "EK1").upper())
        if notice:
            return Response(notice)
        html = render_sozlesme_html(sozlesme) + onay_blogu_html(sozlesme)
        return Response({"html": html, "dondurulmus": False})


class SozlesmeBelgeOlusturView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def get(self, request, pk):
        sozlesme = get_object_or_404(Sozlesme, pk=pk, eczane_id=request.user.eczane_id)
        return _generated_contract_response(sozlesme, (request.query_params.get("belge_turu") or "EK1").upper())


class SozlesmeIslakImzaIndir(APIView):
    """GET /api/abonelik/sozlesmeler/{pk}/islak-imza-indir/ — ıslak imza belgesini proxy et."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdminOrEczaci]

    def get(self, request, pk):
        from django.http import StreamingHttpResponse
        import mimetypes

        qs = Sozlesme.objects.filter(pk=pk)
        if request.user.rol == "pharmacist":
            qs = qs.filter(eczane_id=request.user.eczane_id)
        sozlesme = qs.first()
        if sozlesme is None:
            return Response({"detail": "Sözleşme bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        belge_turu = (request.query_params.get("belge_turu") or "SOZLESME_EK1").upper()
        if belge_turu not in ("SOZLESME_EK1", "EK2"):
            return Response({"detail": "Geçersiz belge türü."}, status=400)
        object_key = sozlesme.ek2_islak_imza_url if belge_turu == "EK2" else sozlesme.islak_imza_url
        if not object_key:
            return Response({"detail": "Islak imza belgesi yüklenmemiş."}, status=status.HTTP_404_NOT_FOUND)

        try:
            from apps.core.services.storage_service import StorageService
            storage = StorageService()
            response_obj = storage.client.get_object(storage.bucket_name, object_key)
            content_type, _ = mimetypes.guess_type(object_key)
            content_type = content_type or "application/octet-stream"
            filename = object_key.rsplit("/", 1)[-1]
            http_response = StreamingHttpResponse(
                streaming_content=response_obj,
                content_type=content_type,
            )
            http_response["Content-Disposition"] = f'inline; filename="{filename}"'
            return http_response
        except Exception as exc:
            logger.exception("Islak imza indirme hatası")
            return Response({"detail": f"Dosya alınamadı: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    @action(detail=False, methods=["get"], url_path="onay-bekleyen")
    def onay_bekleyen(self, request):
        """Eczacı onayı alınmamış aktif sözleşme sayısı (admin)."""
        sayi = Sozlesme.objects.filter(
            durum=Sozlesme.Durum.AKTIF, imza_tipi=Sozlesme.ImzaTipi.DIJITAL,
            eczaci_onay_tarihi__isnull=True,
        ).count()
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
        tarih_baslangic = self.request.query_params.get("tarih_baslangic")
        if tarih_baslangic:
            qs = qs.filter(odeme_tarihi__gte=tarih_baslangic)
        tarih_bitis = self.request.query_params.get("tarih_bitis")
        if tarih_bitis:
            qs = qs.filter(odeme_tarihi__lte=tarih_bitis)
        return qs
