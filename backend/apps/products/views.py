"""Urun yonetim gorunumleri (UoW ile yazma)."""
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.core.uow import UnitOfWork
from apps.pharmacies.auth import KioskAppKeyAuthentication
from apps.pharmacies.permissions import IsKioskOrAuthenticated, IsSuperAdmin

from .models import Cevap, EtkenMadde, Kategori, Soru
from .serializers import (
    CevapWriteSerializer,
    EtkenMaddeSerializer,
    KategoriSerializer,
    KategoriSyncSerializer,
    SoruSerializer,
)


class _UoWWritableViewSet(viewsets.ModelViewSet):
    """Tum yazma islemlerini UoW uzerinden yapan ortak ViewSet."""

    def perform_create(self, serializer):
        instance = serializer.Meta.model(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = serializer.instance
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)

    def perform_destroy(self, instance):
        with UnitOfWork(user=self.request.user) as uow:
            uow.delete(instance)


class UrunSyncView(APIView):
    """GET /api/products/sync/ â€” kiosk yerel DB icin tam katalog."""

    authentication_classes = [JWTAuthentication, KioskAppKeyAuthentication]
    permission_classes = [IsKioskOrAuthenticated]

    def get(self, request):
        kategoriler = Kategori.objects.filter(aktif=True).prefetch_related(
            "sorular__cevaplar",
            "sorular__hedef_cinsiyetler",
            "sorular__hedef_yas_araliklari",
            "hedef_cinsiyetler",
            "hedef_yas_araliklari",
        )
        etken_maddeler = EtkenMadde.objects.all()
        return Response(
            {
                "kategoriler": KategoriSyncSerializer(kategoriler, many=True).data,
                "etken_maddeler": EtkenMaddeSerializer(etken_maddeler, many=True).data,
            }
        )


class _M2MHedeflemeViewSet(_UoWWritableViewSet):
    """Cinsiyet/yas hedefleme M2M alanlarini UoW ile kaydeden ViewSet."""

    _M2M_FIELDS = ("hedef_cinsiyetler", "hedef_yas_araliklari")

    def perform_create(self, serializer):
        m2m = {k: serializer.validated_data.pop(k, []) for k in self._M2M_FIELDS}
        instance = serializer.Meta.model(**serializer.validated_data)
        with UnitOfWork(user=self.request.user) as uow:
            uow.add(instance)
            for fname, val in m2m.items():
                getattr(instance, fname).set(val)
        serializer.instance = instance

    def perform_update(self, serializer):
        instance = serializer.instance
        m2m = {k: serializer.validated_data.pop(k, None) for k in self._M2M_FIELDS}
        for k, v in serializer.validated_data.items():
            setattr(instance, k, v)
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)
            for fname, val in m2m.items():
                if val is not None:
                    getattr(instance, fname).set(val)


class KategoriViewSet(_M2MHedeflemeViewSet):
    queryset = Kategori.objects.prefetch_related(
        "hedef_cinsiyetler", "hedef_yas_araliklari"
    ).all()
    serializer_class = KategoriSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]


class SoruViewSet(_M2MHedeflemeViewSet):
    queryset = Soru.objects.select_related("kategori").prefetch_related(
        "cevaplar", "hedef_cinsiyetler", "hedef_yas_araliklari"
    ).all()
    serializer_class = SoruSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]


class CevapViewSet(_UoWWritableViewSet):
    queryset = Cevap.objects.select_related("soru").all()
    serializer_class = CevapWriteSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]


class EtkenMaddeViewSet(_UoWWritableViewSet):
    queryset = EtkenMadde.objects.all()
    serializer_class = EtkenMaddeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

