"""
Analitik gorunumleri.

Kiosk: oturum ve reklam gosterim verilerini toplu gonderir (idempotent).
Admin: istatistikler ve sayfalanmis liste.

Yazma yolu UoW uzerindendir; ancak kiosk push akisinda kullanici yoktur
(kiosk anonim cihaz), bu yuzden olusturan/guncelleyen NULL kalir.
"""
from datetime import timedelta
import re

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.core.uow import UnitOfWork
from apps.lookups.models import Cinsiyet, YasAraligi
from apps.pharmacies.permissions import IsEczaci, IsSuperAdmin
from apps.products.models import Kategori

from .models import OturumLogu
from .serializers import (
    OturumLoguItemSerializer,
    OturumLoguSerializer,
)


def _OrPerm(*perms):
    class _C(BasePermission):
        def has_permission(self, request, view):
            return any(p().has_permission(request, view) for p in perms)
    return _C


class OturumLoguPagination(CursorPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200
    ordering = "-id"


class OturumLoguView(APIView):
    """GET /api/analytics/sessions/ — panel (admin/eczaci) listesi ve QR sorgusu.

    NOT: Kiosk oturum YAZMA yolu artik bu endpoint'te DEGILDIR; kiosk
    ``POST /api/kiosk/v1/sessions/`` (kiosk_api facade) kullanir. Bu view
    yalniz JWT panel kullanicilari icindir.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [_OrPerm(IsSuperAdmin, IsEczaci)]

    # â”€â”€ GET: Admin/Eczaci listesi â”€â”€
    def get(self, request):
        qr_pattern = re.compile(r"^[0-9A-Z]{8}$")
        qs = (
            OturumLogu.objects.select_related(
                "kiosk__eczane", "kategori", "yas_araligi", "cinsiyet"
            )
            .all()
            .order_by("-olusturulma_tarihi")
        )
        user = request.user
        if getattr(user, "rol", None) == "pharmacist" and not user.eczane_id:
            return Response(
                {"detail": "Bu işlemi yapmak için bir eczaneye bağlı olmalısınız."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qr_kodu = (
            request.query_params.get("qr_kodu")
            or request.query_params.get("qr_code")
            or request.query_params.get("qr")
        )
        if qr_kodu is not None:
            qr_kodu = str(qr_kodu).strip()
            if not qr_kodu:
                return Response(
                    {"detail": "QR kodu giriniz."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not qr_pattern.match(qr_kodu):
                return Response(
                    {"detail": "Geçersiz QR kodu."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            oturum = qs.filter(qr_kodu=qr_kodu).first()
            if not oturum:
                return Response(
                    {"detail": "QR koduna ait oturum bulunamadı."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if getattr(user, "rol", None) == "pharmacist" and oturum.kiosk.eczane_id != user.eczane_id:
                return Response(
                    {"detail": "Bu QR kodu eczanenize ait değildir."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = OturumLoguSerializer(oturum, context={"include_detail_fields": True})
            return Response(serializer.data, status=status.HTTP_200_OK)

        if getattr(user, "rol", None) == "pharmacist":
            qs = qs.filter(kiosk__eczane_id=user.eczane_id)

        hassas = request.query_params.get("hassas_akis") or request.query_params.get("is_sensitive_flow")
        if hassas is not None:
            qs = qs.filter(hassas_akis=str(hassas).lower() == "true")

        paginator = OturumLoguPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = OturumLoguSerializer(page, many=True, context={"include_detail_fields": False})
        return paginator.get_paginated_response(serializer.data)


class OturumLoguCompleteView(APIView):
    """POST /api/analytics/sessions/{id}/complete/

    Eczacının bir QR danışmasını tamamlandı olarak işaretlemesini sağlar.
    - Yalnızca eczacılar kullanabilir.
    - Eczacı yalnızca kendi eczanesine ait kioskların oturumlarını güncelleyebilir.
    - Idempotent: Tekrar tekrar çağrılsa bile yalnızca ilk seferde günceller.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def post(self, request, pk=None):
        user = request.user
        if not user.eczane_id:
            return Response(
                {"detail": "Bu işlemi yapmak için bir eczaneye bağlı olmalısınız."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            oturum = OturumLogu.objects.get(pk=pk, kiosk__eczane_id=user.eczane_id)
        except OturumLogu.DoesNotExist:
            return Response(
                {"detail": "Oturum bulunamadı veya bu oturuma erişim yetkiniz yok."},
                status=status.HTTP_404_NOT_FOUND,
            )

        sale_result = request.data.get("sale_result") or request.data.get("satis_sonucu")
        if sale_result not in (None, "sold", "not_sold"):
            return Response(
                {"detail": "Geçersiz satış sonucu. 'sold' veya 'not_sold' olmalıdır."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if oturum.danisma_tamamlandi:
            # Zaten tamamlanmış, mevcut durumu döndür (idempotency).
            serializer = OturumLoguSerializer(
                oturum,
                context={"include_detail_fields": True, "sale_result": sale_result},
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        oturum.danisma_tamamlandi = True
        oturum.danisma_tamamlanma_tarihi = timezone.now()
        oturum.danisma_tamamlayan_eczaci = user
        oturum.danisma_notu = request.data.get("note", "") or request.data.get("not", "")

        with UnitOfWork(user=user) as uow:
            uow.update(
                oturum,
                update_fields=[
                    "danisma_tamamlandi",
                    "danisma_tamamlanma_tarihi",
                    "danisma_tamamlayan_eczaci",
                    "danisma_notu",
                    "guncellenme_tarihi",
                    "guncelleyen",
                    "surum",
                ],
            )

        serializer = OturumLoguSerializer(
            oturum,
            context={"include_detail_fields": True, "sale_result": sale_result},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class OturumLoguStatsView(APIView):
    """GET /api/analytics/sessions/stats/ — super admin istatistikleri."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        qs = OturumLogu.objects.all()
        toplam = qs.count()

        yas_dagilim = {
            row["yas_araligi__kod"]: row["count"]
            for row in qs.values("yas_araligi__kod").annotate(count=Count("id"))
        }
        cinsiyet_dagilim = {
            row["cinsiyet__kod"]: row["count"]
            for row in qs.values("cinsiyet__kod").annotate(count=Count("id"))
        }
        kategori_dagilim = [
            {"ad": row["kategori__ad"], "sayi": row["count"]}
            for row in qs.values("kategori__ad").annotate(count=Count("id")).order_by("-count")
        ]

        otuz_gun_once = timezone.now() - timedelta(days=30)
        gunluk = [
            {"tarih": str(row["tarih"]), "sayi": row["count"]}
            for row in (
                qs.filter(olusturulma_tarihi__gte=otuz_gun_once)
                .annotate(tarih=TruncDate("olusturulma_tarihi"))
                .values("tarih")
                .annotate(count=Count("id"))
                .order_by("tarih")
            )
        ]

        return Response(
            {
                "toplam_oturum": toplam,
                "yas_araligi_dagilimi": yas_dagilim,
                "cinsiyet_dagilimi": cinsiyet_dagilim,
                "kategori_dagilimi": kategori_dagilim,
                "gunluk_dagilim": gunluk,
            }
        )


class AdminDashboardView(APIView):
    """GET /api/analytics/admin-dashboard/ — Süper admin genel bakış istatistikleri."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        from apps.campaigns.models import Campaign
        from apps.pharmacies.models import Eczane, Kiosk

        now = timezone.now()
        bugun_baslangic = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yedi_gun_once = now - timedelta(days=7)

        toplam_eczane = Eczane.objects.filter(aktif=True).count()
        toplam_kiosk = Kiosk.objects.count()
        aktif_kiosk = Kiosk.objects.filter(
            son_goruldu__gte=now - timedelta(minutes=15)
        ).count()
        aktif_reklam = Campaign.objects.filter(
            status=Campaign.Status.ACTIVE,
            start_date__lte=now,
            end_date__gte=now,
        ).count()
        bugunki_oturum = OturumLogu.objects.filter(
            olusturulma_tarihi__gte=bugun_baslangic
        ).count()

        # Son 7 günlük trend
        haftalik = [
            {"tarih": str(row["tarih"]), "sayi": row["count"]}
            for row in (
                OturumLogu.objects.filter(olusturulma_tarihi__gte=yedi_gun_once)
                .annotate(tarih=TruncDate("olusturulma_tarihi"))
                .values("tarih")
                .annotate(count=Count("id"))
                .order_by("tarih")
            )
        ]

        # Kategori dağılımı
        kategori_dagilim = [
            {"ad": row["kategori__ad"], "slug": row["kategori__slug"], "sayi": row["count"]}
            for row in (
                OturumLogu.objects.values("kategori__ad", "kategori__slug")
                .annotate(count=Count("id"))
                .order_by("-count")[:5]
            )
        ]

        # Son kampanyalar (DOOH v2)
        son_reklamlar = [
            {
                "id": str(row["id"]),
                "ad": row["name"],
                "musteri": str(row["advertiser_id"]) if row["advertiser_id"] else "",
                "baslangic_tarihi": row["start_date"],
                "bitis_tarihi": row["end_date"],
            }
            for row in Campaign.objects.filter(status=Campaign.Status.ACTIVE)
            .values("id", "name", "advertiser_id", "start_date", "end_date", "olusturulma_tarihi")
            .order_by("-olusturulma_tarihi")[:5]
        ]

        return Response(
            {
                "toplam_eczane": toplam_eczane,
                "toplam_kiosk": toplam_kiosk,
                "aktif_kiosk": aktif_kiosk,
                "cevrimdisi_kiosk": toplam_kiosk - aktif_kiosk,
                "aktif_reklam": aktif_reklam,
                "bugunki_oturum": bugunki_oturum,
                "haftalik_trend": haftalik,
                "kategori_dagilim": kategori_dagilim,
                "son_reklamlar": son_reklamlar,
            }
        )

