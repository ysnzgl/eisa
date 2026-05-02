"""
Kampanya yönetim görünümleri.
Admin: tam CRUD (süper admin JWT).
Kiosk: /sync/ endpoint'i ile eczaneye hedeflenmiş aktif kampanyaları alır (App-Key).
"""
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.pharmacies.auth import KioskAppKeyAuthentication
from apps.pharmacies.models import Kiosk
from apps.pharmacies.permissions import IsKiosk, IsSuperAdmin

from .models import Campaign
from .serializers import CampaignSerializer


class CampaignViewSet(viewsets.ModelViewSet):
    """
    Kampanya CRUD endpoint'leri — süper admin JWT ile korumalı.
    /sync/ — Kiosk'un eczanesine göre hedeflenmiş aktif kampanyaları döner (App-Key).
    """

    queryset = Campaign.objects.all().order_by("-created_at")
    serializer_class = CampaignSerializer

    def get_authenticators(self):
        """sync endpoint'i App-Key; diğerleri JWT ile doğrulanır."""
        if getattr(self, "action", None) == "sync":
            return [KioskAppKeyAuthentication()]
        return [JWTAuthentication()]

    def get_permissions(self):
        """sync endpoint'i kiosk'a açık; diğer işlemler süper admin gerektirir."""
        if self.action == "sync":
            return [IsKiosk()]
        return [IsSuperAdmin()]

    @action(detail=False, methods=["get"], url_path="sync")
    def sync(self, request):
        """
        GET /api/campaigns/sync/
        Kioskin bağlı olduğu eczanenin şehir ve ilçesine göre filtrelenmiş,
        şu anda aktif kampanyaları döner.
        Boş target_cities / target_districts listesi "herkese hedefli" anlamına gelir.
        """
        kiosk: Kiosk = request.user
        pharmacy = kiosk.pharmacy
        now = timezone.now()

        # Zaman aralığı filtresi: şu an yayında olan kampanyalar
        qs = Campaign.objects.filter(is_active=True, starts_at__lte=now, ends_at__gte=now)

        # Şehir filtresi: boş liste (herkese) VEYA eczane şehrini içerenler
        qs = qs.filter(
            Q(target_cities=[]) | Q(target_cities__contains=[pharmacy.city])
        )

        # İlçe filtresi: boş liste (herkese) VEYA eczane ilçesini içerenler
        qs = qs.filter(
            Q(target_districts=[]) | Q(target_districts__contains=[pharmacy.district])
        )

        serializer = CampaignSerializer(qs.distinct(), many=True)
        return Response(serializer.data)
