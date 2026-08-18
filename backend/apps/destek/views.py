"""Görüş ve Destek view'leri.

Permissions:
  list, retrieve, yorum_ekle : IsAuthenticated (queryset izolasyonu)
  create                     : IsEczaci
  durum_degistir, yeni_sayisi: IsSuperAdmin
"""
import logging

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.uow import UnitOfWork
from apps.pharmacies.permissions import IsEczaci, IsSuperAdmin
from apps.users.models import Kullanici
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from .models import DestekParametresi, DestekTalebi, DestekYorumu, TalepSayac
from .serializers import (
    DestekDurumGuncelleSerializer,
    DestekParametresiSerializer,
    DestekTalebiCreateSerializer,
    DestekTalebiDetailSerializer,
    DestekTalebiListSerializer,
    DestekYorumuSerializer,
)

logger = logging.getLogger(__name__)

_ACIK_DURUMLAR = {"YENI", "INCELENIYOR", "YANITLANDI"}
_KAPALI_DURUMLAR = {"KAPATILDI"}


class TalepPaginator(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ── Parametre listesi ──────────────────────────────────────────────────────────

from rest_framework.views import APIView


class DestekParametresiListView(APIView):
    """GET /api/destek/parametreler/ — aktif destek parametrelerini döner."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = DestekParametresi.objects.filter(aktif=True).select_related("ust_parametre")
        return Response(DestekParametresiSerializer(qs, many=True).data)


# ── Talep ViewSet ──────────────────────────────────────────────────────────────

class DestekTalebiViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    authentication_classes = [JWTAuthentication]
    pagination_class = TalepPaginator

    def get_permissions(self):
        if self.action == "create":
            return [IsEczaci()]
        if self.action in ("durum_degistir", "yeni_sayisi"):
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return DestekTalebiCreateSerializer
        if self.action == "retrieve":
            return DestekTalebiDetailSerializer
        return DestekTalebiListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = DestekTalebi.objects.select_related(
            "eczane",
            "olusturan_kullanici",
            "talep_turu",
            "alan",
            "alt_konu",
            "durum",
            "kiosk",
        )

        if self.action == "retrieve":
            qs = qs.prefetch_related(
                Prefetch(
                    "yorumlar",
                    queryset=DestekYorumu.objects.select_related("olusturan").order_by(
                        "olusturulma_tarihi"
                    ),
                )
            )

        # Queryset izolasyonu — pharmacy user yalnızca kendi eczanesinin ticketlarını görür.
        if isinstance(user, Kullanici) and user.rol == Kullanici.Rol.ECZACI:
            if not user.eczane_id:
                return qs.none()
            qs = qs.filter(eczane_id=user.eczane_id)

        # ── Filtreler ──────────────────────────────────────────────────────────
        params = self.request.query_params

        if eczane_id := params.get("eczane_id"):
            qs = qs.filter(eczane_id=eczane_id)

        if talep_turu_kod := params.get("talep_turu_kod"):
            qs = qs.filter(talep_turu__kod=talep_turu_kod)

        if alan_kod := params.get("alan_kod"):
            qs = qs.filter(alan__kod=alan_kod)

        if alt_konu_kod := params.get("alt_konu_kod"):
            qs = qs.filter(alt_konu__kod=alt_konu_kod)

        if durum_kod := params.get("durum_kod"):
            qs = qs.filter(durum__kod=durum_kod)

        durum_kategori = params.get("durum_kategori")
        if durum_kategori == "acik":
            qs = qs.filter(durum__kod__in=_ACIK_DURUMLAR)
        elif durum_kategori == "kapali":
            qs = qs.filter(durum__kod__in=_KAPALI_DURUMLAR)

        if baslangic := params.get("baslangic_tarihi"):
            qs = qs.filter(olusturulma_tarihi__date__gte=baslangic)

        if bitis := params.get("bitis_tarihi"):
            qs = qs.filter(olusturulma_tarihi__date__lte=bitis)

        if talep_no := params.get("talep_no"):
            qs = qs.filter(talep_no__icontains=talep_no.strip())

        return qs.order_by("-son_hareket_tarihi")

    def perform_create(self, serializer):
        user = self.request.user
        eczane = user.eczane

        alan = serializer.validated_data["alan_id"]
        alt_konu = serializer.validated_data["alt_konu_id"]
        kiosk = serializer.validated_data.get("kiosk_id")

        # KIOSK > Cihaz seçiminde eczanede tek kiosk varsa otomatik ata.
        if alan.kod == "KIOSK" and alt_konu.kod == "KIOSK_CIHAZ" and kiosk is None:
            kiosklar = list(eczane.kiosklar.filter(aktif=True))
            if len(kiosklar) == 1:
                kiosk = kiosklar[0]
            elif len(kiosklar) > 1:
                from rest_framework.exceptions import ValidationError
                raise ValidationError(
                    {"kiosk_id": "Kiosk > Cihaz seçiminde eczanenizde birden fazla kiosk bulunduğu için kiosk seçimi zorunludur."}
                )

        try:
            yeni_durum = DestekParametresi.objects.get(kod="YENI")
        except DestekParametresi.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Sistem parametresi eksik: YENI durumu bulunamadı.")

        yil = timezone.now().year

        with transaction.atomic():
            sayac, _ = TalepSayac.objects.select_for_update().get_or_create(
                yil=yil, defaults={"son_sayi": 0}
            )
            sayac.son_sayi += 1
            sayac.save(update_fields=["son_sayi"])
            talep_no = f"EISA-{yil}-{sayac.son_sayi:06d}"

            instance = DestekTalebi(
                talep_no=talep_no,
                eczane=eczane,
                olusturan_kullanici=user,
                talep_turu=serializer.validated_data["talep_turu_id"],
                alan=alan,
                alt_konu=alt_konu,
                durum=yeni_durum,
                kiosk=kiosk,
                aciklama=serializer.validated_data["aciklama"],
            )
            with UnitOfWork(user=user) as uow:
                uow.add(instance)

        serializer.instance = instance

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            DestekTalebiDetailSerializer(
                serializer.instance,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Yorum ekle ──────────────────────────────────────────────────────────────

    @action(methods=["post"], detail=True, url_path="yorum-ekle")
    def yorum_ekle(self, request, pk=None):
        talep = self.get_object()

        if talep.durum.kod == "KAPATILDI":
            return Response(
                {"detail": "Kapatılmış talebe yorum eklenemez."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = DestekYorumuSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        yorum = DestekYorumu(
            talep=talep,
            yorum_metni=ser.validated_data["yorum_metni"],
        )
        with UnitOfWork(user=request.user) as uow:
            uow.add(yorum)

        # Durum otomatik geçişleri + son hareket güncelleme.
        yeni_durum_obj = None
        if isinstance(request.user, Kullanici):
            if request.user.rol == Kullanici.Rol.SUPERADMIN:
                yeni_durum_obj = DestekParametresi.objects.filter(kod="YANITLANDI").first()
            elif request.user.rol == Kullanici.Rol.ECZACI and talep.durum.kod == "YANITLANDI":
                yeni_durum_obj = DestekParametresi.objects.filter(kod="INCELENIYOR").first()

        update_kwargs = {"son_hareket_tarihi": timezone.now()}
        if yeni_durum_obj:
            update_kwargs["durum"] = yeni_durum_obj

        DestekTalebi.objects.filter(pk=talep.pk).update(**update_kwargs)

        return Response(DestekYorumuSerializer(yorum).data, status=status.HTTP_201_CREATED)

    # ── Admin: durum değiştir ──────────────────────────────────────────────────

    @action(methods=["patch"], detail=True, url_path="durum-degistir")
    def durum_degistir(self, request, pk=None):
        talep = self.get_object()
        ser = DestekDurumGuncelleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        yeni_durum = ser.get_durum()
        DestekTalebi.objects.filter(pk=talep.pk).update(
            durum=yeni_durum,
            son_hareket_tarihi=timezone.now(),
        )
        talep.refresh_from_db(fields=["durum_id", "son_hareket_tarihi"])

        return Response(
            DestekTalebiListSerializer(talep, context={"request": request}).data
        )

    # ── Admin: yeni talep sayısı (badge) ──────────────────────────────────────

    @action(methods=["get"], detail=False, url_path="yeni-sayisi")
    def yeni_sayisi(self, request):
        sayi = DestekTalebi.objects.filter(durum__kod="YENI").count()
        return Response({"sayi": sayi})
