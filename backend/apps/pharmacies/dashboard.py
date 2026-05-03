"""
Eczacı paneli ana sayfa görünümü — kendi eczanesine ait özet metrikler.

GET /api/pharmacies/me/dashboard/
Yalnızca rolü 'pharmacist' olan ve bir eczaneye bağlı kullanıcılara açıktır.

KVKK uyumu: Tüm sayımlar request.user.pharmacy_id üzerinden filtrelenir;
başka eczanenin verileri SIZDIRILMAZ.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.analytics.models import SessionLog
from apps.campaigns.models import Campaign
from apps.products.models import Category

from .models import Kiosk
from .permissions import IsPharmacist


# Kiosk son temas süresi (saniye) — bu süreden eski ise 'offline' kabul edilir.
HEALTH_OFFLINE_THRESHOLD_SECONDS = 15 * 60  # 15 dakika
HEALTH_DEGRADED_THRESHOLD_SECONDS = 5 * 60  # 5 dakika


def _kiosk_health(last_seen_at):
    """Kiosk son temas zamanına göre 'online' / 'degraded' / 'offline' döner."""
    if last_seen_at is None:
        return "offline"
    age = (timezone.now() - last_seen_at).total_seconds()
    if age <= HEALTH_DEGRADED_THRESHOLD_SECONDS:
        return "online"
    if age <= HEALTH_OFFLINE_THRESHOLD_SECONDS:
        return "degraded"
    return "offline"


class PharmacistDashboardView(APIView):
    """Eczacı ana sayfa: kiosk sayısı, kategori sayısı, oturum sayısı,
    kampanya sayısı ve kiosk health durumları."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsPharmacist]

    def get(self, request):
        user = request.user
        pharmacy = user.pharmacy
        if pharmacy is None:
            return Response(
                {
                    "kiosk_count": 0,
                    "category_count": 0,
                    "session_count": 0,
                    "session_count_today": 0,
                    "campaign_count": 0,
                    "kiosks": [],
                    "warning": "Hesabınıza eczane bağlı değil.",
                }
            )

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        kiosks = list(
            Kiosk.objects.filter(pharmacy_id=pharmacy.id).order_by("id")
        )

        # Bu eczanenin kioskları üzerinden işlem (oturum) sayıları
        kiosk_ids = [k.id for k in kiosks]
        session_qs = SessionLog.objects.filter(kiosk_id__in=kiosk_ids) if kiosk_ids else SessionLog.objects.none()
        session_count = session_qs.count()
        session_count_today = session_qs.filter(created_at__gte=today_start).count()

        # Eczaneye yayında olan kampanyalar (admin DOOH kampanyaları, şehir/ilçe hedefli)
        campaign_qs = Campaign.objects.filter(
            is_active=True, starts_at__lte=now, ends_at__gte=now
        )
        # Boş target_cities = "herkese hedefli" anlamına gelir
        from django.db.models import Q

        campaign_qs = campaign_qs.filter(
            Q(target_cities=[]) | Q(target_cities__contains=[pharmacy.city])
        ).filter(
            Q(target_districts=[]) | Q(target_districts__contains=[pharmacy.district])
        )
        campaign_count = campaign_qs.distinct().count()

        category_count = Category.objects.filter(is_active=True).count()

        kiosks_payload = [
            {
                "id": k.id,
                "mac_address": k.mac_address,
                "is_active": k.is_active,
                "last_seen_at": k.last_seen_at,
                "health": _kiosk_health(k.last_seen_at),
            }
            for k in kiosks
        ]

        return Response(
            {
                "pharmacy": {
                    "id": pharmacy.id,
                    "name": pharmacy.name,
                    "city": pharmacy.city,
                    "district": pharmacy.district,
                },
                "kiosk_count": len(kiosks),
                "category_count": category_count,
                "session_count": session_count,
                "session_count_today": session_count_today,
                "campaign_count": campaign_count,
                "kiosks": kiosks_payload,
            }
        )
