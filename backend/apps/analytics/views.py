"""
Analitik gorunumleri.

Kiosk: oturum ve reklam gosterim verilerini toplu gonderir (idempotent).
Admin: istatistikler ve sayfalanmis liste.

Yazma yolu UoW uzerindendir; ancak kiosk push akisinda kullanici yoktur
(kiosk anonim cihaz), bu yuzden olusturan/guncelleyen NULL kalir.
"""
from datetime import date, datetime, time, timedelta
import calendar
from zoneinfo import ZoneInfo
import re

from django.db.models import Count, Q
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.core.uow import UnitOfWork
from apps.lookups.models import Cinsiyet, YasAraligi
from apps.pharmacies.permissions import IsEczaci, IsSuperAdmin
from apps.products.models import Kategori

from .models import OturumLogu, OturumOnerilenEtkenMadde
from .sales import complete_sale, mark_reviewed
from .serializers import (
    CampaignImpressionSerializer,
    KioskActivityListSerializer,
    KioskEventSerializer,
    OturumLoguItemSerializer,
    OturumLoguSerializer,
)

# Bir COMPLETED oturumun danışılmadan geçmesi gereken süre (EXPIRED türetimi)
EXPIRY_MINUTES = 30


def _OrPerm(*perms):
    class _C(BasePermission):
        def has_permission(self, request, view):
            return any(p().has_permission(request, view) for p in perms)
    return _C


# ─────────────────────────────────────────────────────────────────────────────
# Ortak queryset builder — liste + dashboard aggregation aynı filtre mantığını
# kullanır, sayı tutarsızlığı olmaz.
# ─────────────────────────────────────────────────────────────────────────────

def _build_oturum_queryset(request):
    """Oturum queryset'i: eczane scope + filtreler.

    Pharmacist: yalnız kendi eczanesine ait kiosklar.
    Superadmin: tüm kayıtlar; il/ilçe/eczane filtreleri uygulanabilir.
    """
    qs = (
        OturumLogu.objects
        .select_related(
            "eczane__il",
            "eczane__ilce",
            "kategori",
            "danisma_kategorisi",
            "yas_araligi",
            "cinsiyet",
        )
        .order_by("-olusturulma_tarihi")
    )

    user = request.user
    rol = getattr(user, "rol", None)

    # Eczane scope (pharmacist)
    if rol == "pharmacist":
        if not getattr(user, "eczane_id", None):
            return qs.none()
        qs = qs.filter(Q(eczane_id=user.eczane_id) | Q(eczane__isnull=True, kiosk__eczane_id=user.eczane_id))

    params = request.query_params

    # Admin-only coğrafi filtreler
    if rol != "pharmacist":
        eczane_id = params.get("eczane_id")
        if eczane_id:
            qs = qs.filter(Q(eczane_id=eczane_id) | Q(eczane__isnull=True, kiosk__eczane_id=eczane_id))
        il_id = params.get("il_id")
        if il_id:
            qs = qs.filter(Q(eczane__il_id=il_id) | Q(eczane__isnull=True, kiosk__eczane__il_id=il_id))
        ilce_id = params.get("ilce_id")
        if ilce_id:
            qs = qs.filter(Q(eczane__ilce_id=ilce_id) | Q(eczane__isnull=True, kiosk__eczane__ilce_id=ilce_id))

    # Kiosk filtresi (her iki rol)
    kiosk_id = params.get("kiosk_id")
    if kiosk_id:
        qs = qs.filter(kiosk_id=kiosk_id)

    # Kategori filtresi (drill-down: dashboard donut tıklaması)
    kategori_slug = params.get("kategori_slug")
    if kategori_slug:
        qs = qs.filter(kategori__slug=kategori_slug)

    # Oturum tipi
    oturum_tipi = params.get("oturum_tipi")
    if oturum_tipi:
        qs = qs.filter(oturum_tipi=str(oturum_tipi).upper())

    # Hassas akış
    hassas = params.get("hassas_akis") or params.get("is_sensitive_flow")
    if hassas is not None:
        qs = qs.filter(hassas_akis=str(hassas).lower() in ("true", "1"))

    # Danışma tamamlama durumu
    danisma = params.get("danisma_tamamlandi")
    if danisma is not None:
        qs = qs.filter(danisma_tamamlandi=str(danisma).lower() in ("true", "1"))

    # Durum — EXPIRED read-time türetimi
    durum = params.get("durum")
    if durum:
        durum_upper = str(durum).upper()
        if durum_upper == OturumLogu.Durum.EXPIRED:
            expiry_threshold = timezone.now() - timedelta(minutes=EXPIRY_MINUTES)
            qs = qs.filter(
                durum=OturumLogu.Durum.COMPLETED,
                danisma_tamamlandi=False,
                olusturulma_tarihi__lt=expiry_threshold,
            )
        else:
            qs = qs.filter(durum=durum_upper)

    # Tarih aralığı
    start_date = params.get("start_date")
    if start_date:
        qs = qs.filter(olusturulma_tarihi__date__gte=start_date)
    end_date = params.get("end_date")
    if end_date:
        qs = qs.filter(olusturulma_tarihi__date__lte=end_date)

    # Satış durumu
    sold = params.get("sold")
    if sold is not None:
        if str(sold).lower() in ("true", "1"):
            qs = qs.filter(Q(status=OturumLogu.SatisDurumu.SATIS_YAPILDI) | Q(status=0, sold=True))
        elif str(sold).lower() in ("false", "0"):
            qs = qs.filter(Q(status=OturumLogu.SatisDurumu.SATIS_YAPILMADI) | Q(status=0, sold=False))

    return qs



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

        qs = (
            OturumLogu.objects.select_related(
                "kiosk", "eczane", "kategori", "yas_araligi", "cinsiyet"
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
            from apps.analytics.services import _CROCKFORD_RE
            qr_kodu = str(qr_kodu).strip().upper()
            if not qr_kodu:
                return Response(
                    {"detail": "QR kodu giriniz."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            legacy_pattern = re.compile(r"^[0-9A-Z]{8}$")
            if not legacy_pattern.match(qr_kodu) and not _CROCKFORD_RE.match(qr_kodu):
                return Response(
                    {"detail": "Geçersiz QR kodu."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 9-char Crockford: checksum doğrulama
            if _CROCKFORD_RE.match(qr_kodu):
                from apps.analytics.services import _crockford_checksum_valid
                if not _crockford_checksum_valid(qr_kodu):
                    return Response(
                        {"detail": "Geçersiz QR kodu (hatalı checksum)."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Eczane scope: pharmacist önce kendi eczanesiyle filtreler
            if getattr(user, "rol", None) == "pharmacist":
                oturum = (
                    OturumLogu.objects
                    .select_related("kiosk", "eczane", "kategori", "yas_araligi", "cinsiyet")
                    .filter(eczane_id=user.eczane_id, qr_kodu=qr_kodu)
                    .first()
                )
                if not oturum:
                    # Başka eczanede varlığını sızdırma — her zaman 404
                    return Response(
                        {"detail": "QR koduna ait oturum bulunamadı."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                oturum = (
                    OturumLogu.objects
                    .select_related("kiosk", "eczane", "kategori", "yas_araligi", "cinsiyet")
                    .filter(qr_kodu=qr_kodu)
                    .first()
                )
                if not oturum:
                    return Response(
                        {"detail": "QR koduna ait oturum bulunamadı."},
                        status=status.HTTP_404_NOT_FOUND,
                    )

            serializer = OturumLoguSerializer(oturum, context={"include_detail_fields": True})
            return Response(serializer.data, status=status.HTTP_200_OK)

        if getattr(user, "rol", None) == "pharmacist":
            qs = qs.filter(Q(eczane_id=user.eczane_id) | Q(eczane__isnull=True, kiosk__eczane_id=user.eczane_id))

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
            oturum = complete_sale(
                session_id=pk,
                pharmacy_id=user.eczane_id,
                user=user,
                sale_result=request.data.get("sale_result"),
                note=request.data.get("note", "") or request.data.get("not", ""),
                ingredient_ids=request.data.get("ingredient_ids", request.data.get("satildi_ids", [])),
            )
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        if oturum is None:
            return Response(
                {"detail": "Oturum bulunamadı veya bu oturuma erişim yetkiniz yok."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = OturumLoguSerializer(
            oturum,
            context={"include_detail_fields": True},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class OturumLoguMarkReviewedView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsEczaci]

    def post(self, request, pk=None):
        if not request.user.eczane_id:
            return Response({"detail": "Eczane bağlantısı gerekli."}, status=403)
        session = mark_reviewed(session_id=pk, pharmacy_id=request.user.eczane_id, user=request.user)
        if session is None:
            return Response({"detail": "Oturum bulunamadı veya erişim yetkiniz yok."}, status=404)
        return Response(OturumLoguSerializer(session, context={"include_detail_fields": True}).data)


class DashboardSeriesView(APIView):
    """Admin ve eczacı için İstanbul gün sınırlarıyla 4 dashboard serisi."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [_OrPerm(IsSuperAdmin, IsEczaci)]
    tz = ZoneInfo("Europe/Istanbul")

    def _parse_periods(self, request):
        today = timezone.now().astimezone(self.tz).date()
        try:
            month = date.fromisoformat(f"{request.query_params.get('month', today.strftime('%Y-%m'))}-01")
            week_day = date.fromisoformat(request.query_params.get("week", today.isoformat()))
        except ValueError:
            raise serializers.ValidationError({"detail": "month YYYY-MM, week YYYY-MM-DD biçiminde olmalıdır."})
        if month > today.replace(day=1):
            raise serializers.ValidationError({"month": "Gelecek ay görüntülenemez."})
        week_start = week_day - timedelta(days=week_day.weekday())
        current_week = today - timedelta(days=today.weekday())
        if week_start > current_week:
            raise serializers.ValidationError({"week": "Gelecek hafta görüntülenemez."})
        return today, month, week_start

    def _scoped(self, request):
        qs = OturumLogu.objects.select_related("eczane")
        if getattr(request.user, "rol", None) == "pharmacist":
            return qs.filter(eczane_id=request.user.eczane_id) if request.user.eczane_id else qs.none()
        params = request.query_params
        if params.get("eczane_id"):
            qs = qs.filter(eczane_id=params["eczane_id"])
        if params.get("il_id"):
            qs = qs.filter(eczane__il_id=params["il_id"])
        if params.get("ilce_id"):
            qs = qs.filter(eczane__ilce_id=params["ilce_id"])
        return qs

    def _interaction_series(self, qs, days):
        """QR oturumlarını Danışma kolonundaki sonuç durumuna göre gruplar."""
        values = {
            day: {"pending": 0, "sold": 0, "not_sold": 0}
            for day in days
        }
        start = timezone.make_aware(datetime.combine(days[0], time.min), self.tz)
        end = timezone.make_aware(datetime.combine(days[-1] + timedelta(days=1), time.min), self.tz)
        rows = qs.filter(
            olusturulma_tarihi__gte=start,
            olusturulma_tarihi__lt=end,
        ).values_list("olusturulma_tarihi", "status")
        for stamp, sale_status in rows.iterator():
            if sale_status == OturumLogu.SatisDurumu.SATIS_YAPILDI:
                key = "sold"
            elif sale_status == OturumLogu.SatisDurumu.SATIS_YAPILMADI:
                key = "not_sold"
            else:
                # BEKLIYOR ve INCELENDI henüz satış sonucu olmayan danışmalardır.
                key = "pending"
            values[stamp.astimezone(self.tz).date()][key] += 1
        return [
            {
                "date": day.isoformat(),
                **values[day],
                "value": sum(values[day].values()),
            }
            for day in days
        ]

    def _sales_series(self, qs, days):
        """Günlük önerilen ve satılan etken madde adetlerini birlikte döndürür."""
        recommended = {day: 0 for day in days}
        sold = {day: 0 for day in days}
        start = timezone.make_aware(datetime.combine(days[0], time.min), self.tz)
        end = timezone.make_aware(datetime.combine(days[-1] + timedelta(days=1), time.min), self.tz)
        ingredients = OturumOnerilenEtkenMadde.objects.filter(
            oturum__in=qs,
            oturum__status=OturumLogu.SatisDurumu.SATIS_YAPILDI,
            oturum__result_at__gte=start,
            oturum__result_at__lt=end,
        )

        for stamp, was_sold in ingredients.values_list(
            "oturum__result_at", "satildi"
        ).iterator():
            if stamp:
                day = stamp.astimezone(self.tz).date()
                recommended[day] += 1
                if was_sold:
                    sold[day] += 1

        return [
            {
                "date": day.isoformat(),
                "recommended": recommended[day],
                "sold": sold[day],
                # Eski istemciler için satış değeri korunur.
                "value": sold[day],
            }
            for day in days
        ]

    def get(self, request):
        _, month, week_start = self._parse_periods(request)
        month_days = [month + timedelta(days=i) for i in range(calendar.monthrange(month.year, month.month)[1])]
        week_days = [week_start + timedelta(days=i) for i in range(7)]
        qs = self._scoped(request)
        monthly_interactions = self._interaction_series(qs, month_days)
        monthly_sales = self._sales_series(qs, month_days)
        weekly_interactions = self._interaction_series(qs, week_days)
        weekly_sales = self._sales_series(qs, week_days)
        return Response({
            "timezone": "Europe/Istanbul",
            "month": month.strftime("%Y-%m"),
            "week_start": week_start.isoformat(),
            "week_end": week_days[-1].isoformat(),
            "monthly_interactions": monthly_interactions,
            "monthly_sales": monthly_sales,
            "weekly_interactions": weekly_interactions,
            "weekly_sales": weekly_sales,
            "totals": {
                "monthly_interactions": sum(item["value"] for item in monthly_interactions),
                "monthly_pending": sum(item["pending"] for item in monthly_interactions),
                "monthly_interaction_sold": sum(item["sold"] for item in monthly_interactions),
                "monthly_not_sold": sum(item["not_sold"] for item in monthly_interactions),
                "monthly_sales": sum(item["value"] for item in monthly_sales),
                "monthly_recommended": sum(item["recommended"] for item in monthly_sales),
                "monthly_sold": sum(item["sold"] for item in monthly_sales),
                "weekly_interactions": sum(item["value"] for item in weekly_interactions),
                "weekly_pending": sum(item["pending"] for item in weekly_interactions),
                "weekly_interaction_sold": sum(item["sold"] for item in weekly_interactions),
                "weekly_not_sold": sum(item["not_sold"] for item in weekly_interactions),
                "weekly_sales": sum(item["value"] for item in weekly_sales),
                "weekly_recommended": sum(item["recommended"] for item in weekly_sales),
                "weekly_sold": sum(item["sold"] for item in weekly_sales),
            },
        })


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
        istanbul = ZoneInfo("Europe/Istanbul")
        istanbul_now = now.astimezone(istanbul)
        bugun_baslangic = istanbul_now.replace(hour=0, minute=0, second=0, microsecond=0)
        yarin_baslangic = bugun_baslangic + timedelta(days=1)
        yedi_gun_once = now - timedelta(days=7)
        params = request.query_params
        il_id = params.get("il_id")
        eczane_id = params.get("eczane_id")
        oturum_qs = OturumLogu.objects.all()
        if il_id:
            oturum_qs = oturum_qs.filter(
                Q(eczane__il_id=il_id)
                | Q(eczane__isnull=True, kiosk__eczane__il_id=il_id)
            )
        if eczane_id:
            oturum_qs = oturum_qs.filter(
                Q(eczane_id=eczane_id)
                | Q(eczane__isnull=True, kiosk__eczane_id=eczane_id)
            )

        eczane_qs = Eczane.objects.filter(aktif=True)
        kiosk_qs = Kiosk.objects.all()
        if il_id:
            eczane_qs = eczane_qs.filter(il_id=il_id)
            kiosk_qs = kiosk_qs.filter(eczane__il_id=il_id)
        if eczane_id:
            eczane_qs = eczane_qs.filter(id=eczane_id)
            kiosk_qs = kiosk_qs.filter(eczane_id=eczane_id)

        toplam_eczane = eczane_qs.count()
        toplam_kiosk = kiosk_qs.count()
        aktif_kiosk = kiosk_qs.filter(
            son_goruldu__gte=now - timedelta(minutes=15)
        ).count()
        aktif_reklam_qs = Campaign.objects.filter(
            status=Campaign.Status.ACTIVE,
            start_date__lte=now,
            end_date__gte=now,
        )
        if eczane_id:
            aktif_reklam_qs = aktif_reklam_qs.filter(
                Q(target_pharmacies__isnull=True) | Q(target_pharmacies__id=eczane_id)
            ).distinct()
        elif il_id:
            aktif_reklam_qs = aktif_reklam_qs.filter(
                Q(target_pharmacies__isnull=True) | Q(target_pharmacies__il_id=il_id)
            ).distinct()
        aktif_reklam = aktif_reklam_qs.count()
        bugunki_oturum = oturum_qs.filter(
            olusturulma_tarihi__gte=bugun_baslangic,
            olusturulma_tarihi__lt=yarin_baslangic,
        ).count()

        # Son 7 günlük trend
        haftalik = [
            {"tarih": str(row["tarih"]), "sayi": row["count"]}
            for row in (
                oturum_qs.filter(olusturulma_tarihi__gte=yedi_gun_once)
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
                oturum_qs.filter(kategori__isnull=False)
                .exclude(kategori__ad="")
                .values("kategori__ad", "kategori__slug")
                .annotate(count=Count("id"))
                .order_by("-count", "kategori__ad")[:10]
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
            for row in aktif_reklam_qs
            .values("id", "name", "advertiser_id", "start_date", "end_date", "olusturulma_tarihi")
            .order_by("-olusturulma_tarihi")[:5]
        ]

        # Satış istatistikleri — start_date/end_date parametrelerine duyarlı
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        sold_qs = oturum_qs.filter(
            status=OturumLogu.SatisDurumu.SATIS_YAPILDI,
            result_at__isnull=False,
        )
        if start_date:
            sold_qs = sold_qs.filter(result_at__date__gte=start_date)
        if end_date:
            sold_qs = sold_qs.filter(result_at__date__lte=end_date)
        satis_sayisi = sold_qs.count()
        satis_yapan_eczaneler = [
            {
                "id": row["pharmacy_id"],
                "ad": row["pharmacy_name"] or "Bilinmeyen Eczane",
                "sayi": row["count"],
            }
            for row in (
                sold_qs
                .annotate(
                    pharmacy_id=Coalesce("eczane_id", "kiosk__eczane_id"),
                    pharmacy_name=Coalesce("eczane__ad", "kiosk__eczane__ad"),
                )
                .values("pharmacy_id", "pharmacy_name")
                .annotate(count=Count("id"))
                .order_by("-count", "pharmacy_name")[:10]
            )
        ]

        em_qs = OturumOnerilenEtkenMadde.objects.filter(
            oturum__in=oturum_qs,
            oturum__status=OturumLogu.SatisDurumu.SATIS_YAPILDI,
            oturum__result_at__isnull=False,
            satildi=True,
        )
        if start_date:
            em_qs = em_qs.filter(oturum__result_at__date__gte=start_date)
        if end_date:
            em_qs = em_qs.filter(oturum__result_at__date__lte=end_date)

        satilan_etken_madde_dagilimi = [
            {"ad": row["em_adi"], "sayi": row["sayi"]}
            for row in (
                em_qs
                .annotate(em_adi=Coalesce("etken_madde__ad", "etken_madde_adi_snapshot"))
                .exclude(em_adi__isnull=True)
                .exclude(em_adi="")
                .values("em_adi")
                .annotate(sayi=Count("id"))
                .order_by("-sayi", "em_adi")[:10]
            )
        ]

        top_em = (
            em_qs
            .annotate(em_adi=Coalesce("etken_madde__ad", "etken_madde_adi_snapshot"))
            .values("em_adi")
            .annotate(sayi=Count("id"))
            .order_by("-sayi")
            .first()
        )
        en_cok_satilan = (
            {"ad": top_em["em_adi"], "sayi": top_em["sayi"]} if top_em else None
        )

        # Tüm QR oturumlarındaki öneriler: sağ sütundaki ilk 10 listesi için.
        onerilen_etken_madde_dagilimi = [
            {"ad": row["em_adi"], "sayi": row["sayi"]}
            for row in (
                OturumOnerilenEtkenMadde.objects.filter(oturum__in=oturum_qs)
                .annotate(em_adi=Coalesce("etken_madde__ad", "etken_madde_adi_snapshot"))
                .exclude(em_adi__isnull=True)
                .exclude(em_adi="")
                .values("em_adi")
                .annotate(sayi=Count("id"))
                .order_by("-sayi", "em_adi")[:10]
            )
        ]
        en_cok_onerilen = onerilen_etken_madde_dagilimi[0] if onerilen_etken_madde_dagilimi else None

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
                "satis_sayisi": satis_sayisi,
                "satis_yapan_eczaneler": satis_yapan_eczaneler,
                "en_cok_satilan_etken_madde": en_cok_satilan,
                "satilan_etken_madde_dagilimi": satilan_etken_madde_dagilimi,
                "en_cok_onerilen_etken_madde": en_cok_onerilen,
                "onerilen_etken_madde_dagilimi": onerilen_etken_madde_dagilimi,
            }
        )


# ─────────────────────────────────────────────────────────────────────────────
# Kiosk Hareketleri — oturum listesi (admin + eczacı)
# ─────────────────────────────────────────────────────────────────────────────

class KioskActivityPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class KioskActivityView(APIView):
    """GET /api/analytics/kiosk-activities/

    Kiosk QR/oturum hareketleri listesi.

    Admin: tüm kayıtlar; il_id/ilce_id/eczane_id/kiosk_id ile filtreleme.
    Eczacı: yalnız kendi eczanesine ait kiosklar. Coğrafi filtreler uygulanmaz.

    Query parametreleri:
      kiosk_id, eczane_id (admin), il_id (admin), ilce_id (admin),
      oturum_tipi (SIKAYET|OZEL_DANISMANLIK),
      durum (COMPLETED|ABANDONED|EXPIRED),
      hassas_akis (true|false),
      danisma_tamamlandi (true|false),
      start_date (YYYY-MM-DD), end_date (YYYY-MM-DD),
      page, page_size
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [_OrPerm(IsSuperAdmin, IsEczaci)]

    def get(self, request):
        qs = _build_oturum_queryset(request)
        is_sold_view = request.query_params.get("sold") in ("true", "1")
        if is_sold_view:
            qs = qs.prefetch_related("onerilen_etken_madde_detaylari__etken_madde")
        summary = qs.aggregate(
            recommended=Count("onerilen_etken_madde_detaylari"),
            sold=Count(
                "onerilen_etken_madde_detaylari",
                filter=Q(onerilen_etken_madde_detaylari__satildi=True),
            ),
        )
        paginator = KioskActivityPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = KioskActivityListSerializer(
            page, many=True, context={"include_ingredients": is_sold_view}
        )
        response = paginator.get_paginated_response(serializer.data)
        response.data["summary"] = summary
        return response


# ─────────────────────────────────────────────────────────────────────────────
# Kampanya Gösterimleri — PlayLog listesi (admin + eczacı)
# ─────────────────────────────────────────────────────────────────────────────

class CampaignImpressionView(APIView):
    """GET /api/analytics/campaign-impressions/

    Kiosk'tan gelen reklam gösterim kayıtları (PlayLog).

    Admin: tüm kayıtlar; il_id/ilce_id/eczane_id/kiosk_id/campaign_id filtresi.
    Eczacı: yalnız kendi eczanesine ait kiosk kayıtları.

    Query parametreleri:
      campaign_id, kiosk_id, eczane_id (admin), il_id (admin),
      start_date (YYYY-MM-DD), end_date (YYYY-MM-DD),
      page, page_size
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [_OrPerm(IsSuperAdmin, IsEczaci)]

    def get(self, request):
        from apps.campaigns.models import PlayLog

        qs = (
            PlayLog.objects
            .select_related(
                "kiosk__eczane",
                "creative__campaign",
            )
            .order_by("-played_at")
        )

        user = request.user
        rol = getattr(user, "rol", None)

        # Eczane scope
        if rol == "pharmacist":
            if not getattr(user, "eczane_id", None):
                qs = qs.none()
            else:
                qs = qs.filter(kiosk__eczane_id=user.eczane_id)

        params = request.query_params

        # Admin-only coğrafi filtreler
        if rol != "pharmacist":
            eczane_id = params.get("eczane_id")
            if eczane_id:
                qs = qs.filter(kiosk__eczane_id=eczane_id)
            il_id = params.get("il_id")
            if il_id:
                qs = qs.filter(kiosk__eczane__il_id=il_id)
            ilce_id = params.get("ilce_id")
            if ilce_id:
                qs = qs.filter(kiosk__eczane__ilce_id=ilce_id)

        # Kiosk filtresi
        kiosk_id = params.get("kiosk_id")
        if kiosk_id:
            qs = qs.filter(kiosk_id=kiosk_id)

        # Kampanya filtresi (creative üzerinden)
        campaign_id = params.get("campaign_id")
        if campaign_id:
            qs = qs.filter(creative__campaign_id=campaign_id)

        # Tarih aralığı
        start_date = params.get("start_date")
        if start_date:
            qs = qs.filter(played_at__date__gte=start_date)
        end_date = params.get("end_date")
        if end_date:
            qs = qs.filter(played_at__date__lte=end_date)

        paginator = KioskActivityPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = CampaignImpressionSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


# ─────────────────────────────────────────────────────────────────────────────
# Faz 4 — Kiosk Olayları listesi (admin + eczacı)
# ─────────────────────────────────────────────────────────────────────────────

class KioskEventListView(APIView):
    """GET /api/analytics/kiosk-events/

    Kiosk teknik olayları (hata, bağlantı, restart vb.) listesi.

    Admin: tüm kayıtlar; il_id/eczane_id/kiosk_id filtresi.
    Eczacı: yalnız kendi eczanesine ait kiosk kayıtları.

    Query parametreleri:
      kiosk_id, eczane_id (admin), il_id (admin),
      event_type, severity,
      start_date (YYYY-MM-DD), end_date (YYYY-MM-DD),
      page, page_size
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [_OrPerm(IsSuperAdmin, IsEczaci)]

    def get(self, request):
        from .models import KioskEvent

        qs = (
            KioskEvent.objects
            .select_related("kiosk__eczane")
            .order_by("-olusturulma_tarihi")
        )

        user = request.user
        rol = getattr(user, "rol", None)

        # Eczane scope
        if rol == "pharmacist":
            if not getattr(user, "eczane_id", None):
                qs = qs.none()
            else:
                qs = qs.filter(kiosk__eczane_id=user.eczane_id)

        params = request.query_params

        # Admin-only coğrafi filtreler
        if rol != "pharmacist":
            eczane_id = params.get("eczane_id")
            if eczane_id:
                qs = qs.filter(kiosk__eczane_id=eczane_id)
            il_id = params.get("il_id")
            if il_id:
                qs = qs.filter(kiosk__eczane__il_id=il_id)

        kiosk_id = params.get("kiosk_id")
        if kiosk_id:
            qs = qs.filter(kiosk_id=kiosk_id)

        event_type = params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=str(event_type).upper())

        severity = params.get("severity")
        if severity:
            qs = qs.filter(severity=str(severity).upper())

        start_date = params.get("start_date")
        if start_date:
            qs = qs.filter(olusturulma_tarihi__date__gte=start_date)
        end_date = params.get("end_date")
        if end_date:
            qs = qs.filter(olusturulma_tarihi__date__lte=end_date)

        paginator = KioskActivityPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = KioskEventSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


