"""
Analitik görünümleri.
Kiosk: oturum ve reklam gösterim verilerini toplu gönderir.
Admin (süper admin): istatistikler ve sayfalı oturum listesi.
"""
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.pharmacies.auth import KioskAppKeyAuthentication
from apps.pharmacies.permissions import IsKiosk, IsSuperAdmin
from apps.products.models import Category

from .models import AdImpression, SessionLog
from .serializers import (
    AdImpressionItemSerializer,
    SessionLogItemSerializer,
    SessionLogSerializer,
)


class SessionLogPagination(PageNumberPagination):
    """Oturum log listesi için sayfalama — varsayılan 50, maksimum 200."""

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class SessionLogView(APIView):
    """
    GET  /api/analytics/sessions/ — Süper admin: sayfalı oturum log listesi.
    POST /api/analytics/sessions/ — Kiosk: outbox'tan toplu oturum verisi iletimi.

    Farklı HTTP metodları farklı kimlik doğrulama ve izin sınıfları gerektirir.
    """

    authentication_classes = [JWTAuthentication, KioskAppKeyAuthentication]

    def get_permissions(self):
        """POST → kiosk; GET → süper admin."""
        if self.request.method == "POST":
            return [IsKiosk()]
        return [IsSuperAdmin()]

    # --- GET: Admin oturum listesi ---

    def get(self, request):
        """Tüm oturum kayıtlarını tersten tarihe göre sıralı ve sayfalı döner.
        Desteklenen query params: qr_code, is_sensitive_flow, ordering."""
        queryset = (
            SessionLog.objects.select_related("kiosk__pharmacy", "category")
            .all()
            .order_by("-created_at")
        )
        # qr_code filtresi — QrScan.vue tarafından kullanılır
        qr_code = request.query_params.get("qr_code")
        if qr_code:
            queryset = queryset.filter(qr_code=qr_code.upper())

        # is_sensitive_flow filtresi — Inbox.vue tarafından kullanılır
        is_sensitive = request.query_params.get("is_sensitive_flow")
        if is_sensitive is not None:
            queryset = queryset.filter(is_sensitive_flow=is_sensitive.lower() == "true")

        paginator = SessionLogPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = SessionLogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    # --- POST: Kiosk outbox push ---

    def post(self, request):
        """
        Kiosk outbox'tan gelen oturum kayıtlarını toplu işler.
        Her öğe bağımsız olarak doğrulanır; hatalılar reddedilirken diğerleri kabul edilir.
        Yanıt: {"accepted": N, "errors": [...]}
        """
        items = request.data.get("items", [])
        if not isinstance(items, list):
            return Response(
                {"detail": "'items' alanı bir liste olmalıdır."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        accepted = 0
        errors = []

        for i, item_data in enumerate(items):
            serializer = SessionLogItemSerializer(data=item_data)
            if not serializer.is_valid():
                errors.append({"index": i, "errors": serializer.errors})
                continue

            data = serializer.validated_data
            # Kimlik doğrulamasından gelen kiosk kullanılacağı için kiosk_mac payload'dan çıkar
            data.pop("kiosk_mac", None)
            category_slug = data.pop("category_slug")
            # Kiosk'un orijinal zaman damgasını sakla (auto_now_add'ı aşmak için)
            kiosk_created_at = data.pop("created_at", None)

            try:
                category = Category.objects.get(slug=category_slug)
            except Category.DoesNotExist:
                errors.append(
                    {
                        "index": i,
                        "errors": {
                            "category_slug": [f"'{category_slug}' kategorisi bulunamadı."]
                        },
                    }
                )
                continue

            # Oturumu kaydet (created_at auto_now_add ile server zamanına ayarlanır)
            log = SessionLog.objects.create(
                kiosk=request.user,
                category=category,
                **data,
            )
            # Kiosk'un orijinal zaman damgasını koru (auto_now_add'ı queryset.update ile aş)
            if kiosk_created_at:
                SessionLog.objects.filter(pk=log.pk).update(created_at=kiosk_created_at)

            accepted += 1

        return_status = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_200_OK
        return Response({"accepted": accepted, "errors": errors}, status=return_status)


class AdImpressionBulkPushView(APIView):
    """
    POST /api/analytics/impressions/
    Kiosk'tan gelen toplu reklam gösterim kayıtlarını kabul eder.
    Yanıt: {"accepted": N, "errors": [...]}
    """

    authentication_classes = [KioskAppKeyAuthentication]
    permission_classes = [IsKiosk]

    def post(self, request):
        # İçe aktarımı döngüsel bağımlılığı önlemek için burada yap
        from apps.campaigns.models import Campaign

        items = request.data.get("items", [])
        if not isinstance(items, list):
            return Response(
                {"detail": "'items' alanı bir liste olmalıdır."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        accepted = 0
        errors = []

        for i, item_data in enumerate(items):
            serializer = AdImpressionItemSerializer(data=item_data)
            if not serializer.is_valid():
                errors.append({"index": i, "errors": serializer.errors})
                continue

            data = serializer.validated_data

            try:
                campaign = Campaign.objects.get(pk=data["campaign_id"])
            except Campaign.DoesNotExist:
                errors.append(
                    {"index": i, "errors": {"campaign_id": ["Kampanya bulunamadı."]}}
                )
                continue

            AdImpression.objects.create(
                kiosk=request.user,
                campaign=campaign,
                shown_at=data["shown_at"],
                duration_ms=data.get("duration_ms", 0),
            )
            accepted += 1

        return_status = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_200_OK
        return Response({"accepted": accepted, "errors": errors}, status=return_status)


class SessionLogStatsView(APIView):
    """
    GET /api/analytics/sessions/stats/
    Toplam oturum istatistiklerini döner (sadece süper admin).
    Dönen veriler: toplam, yaş aralığı, cinsiyet, kategori dağılımı ve son 30 günlük trend.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        qs = SessionLog.objects.all()
        total = qs.count()

        # Yaş aralığına göre dağılım: {"18-25": 100, ...}
        by_age_raw = qs.values("age_range").annotate(count=Count("id"))
        by_age = {item["age_range"]: item["count"] for item in by_age_raw}

        # Cinsiyete göre dağılım: {"F": 500, "M": 700, ...}
        by_gender_raw = qs.values("gender").annotate(count=Count("id"))
        by_gender = {item["gender"]: item["count"] for item in by_gender_raw}

        # Kategoriye göre dağılım: [{"name": "Enerji", "count": 300}, ...]
        by_category = list(
            qs.values("category__name")
            .annotate(count=Count("id"))
            .order_by("-count")
            .values("category__name", "count")
        )
        by_category = [
            {"name": item["category__name"], "count": item["count"]}
            for item in by_category
        ]

        # Son 30 günlük günlük dağılım: [{"date": "2025-01-01", "count": 10}, ...]
        thirty_days_ago = timezone.now() - timedelta(days=30)
        by_date_raw = (
            qs.filter(created_at__gte=thirty_days_ago)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )
        by_date = [
            {"date": str(item["date"]), "count": item["count"]} for item in by_date_raw
        ]

        return Response(
            {
                "total_sessions": total,
                "by_age_range": by_age,
                "by_gender": by_gender,
                "by_category": by_category,
                "by_date": by_date,
            }
        )
