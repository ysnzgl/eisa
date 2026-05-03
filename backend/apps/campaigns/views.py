"""
Reklam (Kampanya) gorunumleri.

Admin: tam CRUD (super admin JWT, UoW ile).
Kiosk: /sync/ endpoint'i — kioskun eczanesine hedeflenmis aktif reklamlar.
Bos hedef_eczaneler = herkese goster (genel yayin).
"""
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.core.uow import UnitOfWork
from apps.pharmacies.auth import KioskAppKeyAuthentication
from apps.pharmacies.models import Kiosk
from apps.pharmacies.permissions import IsKiosk, IsSuperAdmin

from .models import Reklam
from .serializers import ReklamSerializer


class ReklamViewSet(viewsets.ModelViewSet):
    queryset = Reklam.objects.prefetch_related("hedef_eczaneler").all()
    serializer_class = ReklamSerializer

    def get_authenticators(self):
        if getattr(self, "action", None) == "sync":
            return [KioskAppKeyAuthentication()]
        return [JWTAuthentication()]

    def get_permissions(self):
        if self.action == "sync":
            return [IsKiosk()]
        return [IsSuperAdmin()]

    # ── UoW ile yazma ──
    def perform_create(self, serializer):
        hedef_eczaneler = serializer.validated_data.pop("hedef_eczaneler", [])
        instance = Reklam(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
            instance.hedef_eczaneler.set(hedef_eczaneler)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance: Reklam = serializer.instance
        hedef_eczaneler = serializer.validated_data.pop("hedef_eczaneler", None)
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)
            if hedef_eczaneler is not None:
                instance.hedef_eczaneler.set(hedef_eczaneler)

    def perform_destroy(self, instance):
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)

    # ── Kiosk sync ──
    @action(detail=False, methods=["get"], url_path="sync")
    def sync(self, request):
        """
        GET /api/campaigns/sync/
        Kioskun eczanesine hedeflenmis, su an aktif reklamlar.
        Bos hedef_eczaneler = herkese hedefli (genel yayin).
        """
        kiosk: Kiosk = request.user
        eczane = kiosk.eczane
        now = timezone.now()

        qs = Reklam.objects.filter(
            aktif=True, baslangic_tarihi__lte=now, bitis_tarihi__gte=now
        )
        # Bos hedef_eczaneler = herkese; yoksa bu eczane dahil olmali
        qs = qs.filter(
            hedef_eczaneler__isnull=True
        ) | qs.filter(
            hedef_eczaneler=eczane
        )
        qs = qs.distinct()

        return Response(ReklamSerializer(qs, many=True).data)
