"""Urun yonetim gorunumleri (UoW ile yazma)."""
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.core.uow import UnitOfWork
from apps.pharmacies.auth import KioskAppKeyAuthentication
from apps.pharmacies.permissions import IsKioskOrAuthenticated, IsSuperAdmin

from .models import Cevap, EtkenMadde, Kategori, Soru, SoruEtkenMadde
from .serializers import (
    CevapWriteSerializer,
    EtkenMaddeSerializer,
    KategoriSerializer,
    KategoriSyncSerializer,
    SoruEtkenMaddeSerializer,
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
    """GET /api/products/sync/ — kiosk yerel DB icin tam katalog."""

    authentication_classes = [JWTAuthentication, KioskAppKeyAuthentication]
    permission_classes = [IsKioskOrAuthenticated]

    def get(self, request):
        kategoriler = Kategori.objects.filter(aktif=True).select_related(
            "hedef_cinsiyet",
        ).prefetch_related(
            "hedef_yas_araliklari",
            "sorular__cevaplar",
            "sorular__hedef_yas_araliklari",
            "sorular__etken_madde_baglantilari__etken_madde",
        )
        etken_maddeler = EtkenMadde.objects.filter(aktif=True)
        return Response(
            {
                "kategoriler": KategoriSyncSerializer(kategoriler, many=True).data,
                "etken_maddeler": EtkenMaddeSerializer(etken_maddeler, many=True).data,
            }
        )


class _M2MHedeflemeViewSet(_UoWWritableViewSet):
    """M2M hedefleme alanlarini UoW ile kaydeden ViewSet.

    Alt siniflar _M2M_FIELDS'i override ederek hangi alanlarin M2M oldugunu belirtir.
    Through model kullanan M2M alanlar buraya EKLENMEZ; kendi ViewSet'leri vardir.
    """

    _M2M_FIELDS: tuple = ()

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
    _M2M_FIELDS = ("hedef_yas_araliklari",)
    queryset = Kategori.objects.select_related(
        "hedef_cinsiyet",
    ).prefetch_related(
        "hedef_yas_araliklari",
    ).all()
    serializer_class = KategoriSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]


class SoruViewSet(_M2MHedeflemeViewSet):
    _M2M_FIELDS = ("hedef_yas_araliklari",)
    queryset = Soru.objects.select_related(
        "kategori", "hedef_cinsiyet",
    ).prefetch_related(
        "cevaplar",
        "hedef_yas_araliklari",
        "etken_madde_baglantilari__etken_madde",
    ).all()
    serializer_class = SoruSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        kategori_id = self.request.query_params.get("kategori")
        if kategori_id:
            qs = qs.filter(kategori_id=kategori_id)
        return qs


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

    def get_queryset(self):
        qs = EtkenMadde.objects.all()
        if self.action == 'list' and not self.request.query_params.get('include_inactive'):
            qs = qs.filter(aktif=True)
        return qs

    def perform_destroy(self, instance):
        instance.aktif = False
        with UnitOfWork(user=self.request.user) as uow:
            uow.update(instance)


class SoruEtkenMaddeViewSet(_UoWWritableViewSet):
    """Soru–EtkenMadde baglantisi CRUD — rol (ana/destekleyici) yonetimi.

    Ayni soruya ayni etken maddeyi eklemek 400 hatasi dondurur.
    Sadece rol guncellenmek istenirse PATCH kullanilabilir.
    """

    queryset = SoruEtkenMadde.objects.select_related(
        "soru", "etken_madde"
    ).all()
    serializer_class = SoruEtkenMaddeSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]
