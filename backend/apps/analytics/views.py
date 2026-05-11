"""
Analitik gorunumleri.

Kiosk: oturum ve reklam gosterim verilerini toplu gonderir (idempotent).
Admin: istatistikler ve sayfalanmis liste.

Yazma yolu UoW uzerindendir; ancak kiosk push akisinda kullanici yoktur
(kiosk anonim cihaz), bu yuzden olusturan/guncelleyen NULL kalir.
"""
from datetime import timedelta

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
from apps.pharmacies.auth import KioskAppKeyAuthentication
from apps.pharmacies.permissions import IsEczaci, IsKiosk, IsSuperAdmin
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
    """GET (admin/eczaci) / POST (kiosk) /api/analytics/sessions/"""

    authentication_classes = [JWTAuthentication, KioskAppKeyAuthentication]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsKiosk()]
        return [_OrPerm(IsSuperAdmin, IsEczaci)()]

    # â”€â”€ GET: Admin/Eczaci listesi â”€â”€
    def get(self, request):
        qs = (
            OturumLogu.objects.select_related(
                "kiosk__eczane", "kategori", "yas_araligi", "cinsiyet"
            )
            .all()
            .order_by("-olusturulma_tarihi")
        )
        user = request.user
        if getattr(user, "rol", None) == "pharmacist":
            if not user.eczane_id:
                return Response({"results": [], "count": 0, "next": None, "previous": None})
            qs = qs.filter(kiosk__eczane_id=user.eczane_id)

        qr_kodu = request.query_params.get("qr_kodu") or request.query_params.get("qr_code")
        if qr_kodu:
            qs = qs.filter(qr_kodu=qr_kodu.upper())

        hassas = request.query_params.get("hassas_akis") or request.query_params.get("is_sensitive_flow")
        if hassas is not None:
            qs = qs.filter(hassas_akis=str(hassas).lower() == "true")

        paginator = OturumLoguPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(OturumLoguSerializer(page, many=True).data)

    # â”€â”€ POST: Kiosk outbox push (idempotent) â”€â”€
    def post(self, request):
        items = request.data.get("items", [])
        if not isinstance(items, list):
            return Response({"detail": "'items' alani bir liste olmalidir."},
                            status=status.HTTP_400_BAD_REQUEST)

        accepted = []
        errors = []

        for i, raw in enumerate(items):
            ser = OturumLoguItemSerializer(data=raw)
            if not ser.is_valid():
                errors.append({"index": i, "idempotency_anahtari": (raw or {}).get("idempotency_anahtari"),
                              "errors": ser.errors})
                continue
            d = ser.validated_data
            idem = d["idempotency_anahtari"]

            if OturumLogu.objects.filter(idempotency_anahtari=idem).exists():
                accepted.append(str(idem))
                continue

            try:
                kategori = Kategori.objects.get(slug=d["kategori_slug"])
            except Kategori.DoesNotExist:
                errors.append({"index": i, "idempotency_anahtari": str(idem),
                              "errors": {"kategori_slug": [f"'{d['kategori_slug']}' kategori yok."]}})
                continue
            try:
                yas = YasAraligi.objects.get(kod=d["yas_araligi_kod"])
            except YasAraligi.DoesNotExist:
                errors.append({"index": i, "idempotency_anahtari": str(idem),
                              "errors": {"yas_araligi_kod": [f"Yas araligi yok: {d['yas_araligi_kod']}"]}})
                continue
            try:
                cins = Cinsiyet.objects.get(kod=d["cinsiyet_kod"])
            except Cinsiyet.DoesNotExist:
                errors.append({"index": i, "idempotency_anahtari": str(idem),
                              "errors": {"cinsiyet_kod": [f"Cinsiyet yok: {d['cinsiyet_kod']}"]}})
                continue

            instance = OturumLogu(
                idempotency_anahtari=idem,
                kiosk=request.user,
                kategori=kategori,
                yas_araligi=yas,
                cinsiyet=cins,
                hassas_akis=d.get("hassas_akis", False),
                qr_kodu=d["qr_kodu"],
                cevaplar=d.get("cevaplar", {}),
                onerilen_etken_maddeler=d.get("onerilen_etken_maddeler", []),
            )
            with UnitOfWork(user=None) as uow:
                uow.add(instance)
            kiosk_ts = d.get("olusturulma_tarihi")
            if kiosk_ts:
                OturumLogu.objects.filter(pk=instance.pk).update(olusturulma_tarihi=kiosk_ts)
            accepted.append(str(idem))

        return_status = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_200_OK
        return Response({"accepted": len(accepted), "accepted_keys": accepted, "errors": errors},
                        status=return_status)


class OturumLoguStatsView(APIView):
    """GET /api/analytics/sessions/stats/ â€” super admin istatistikleri."""

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

