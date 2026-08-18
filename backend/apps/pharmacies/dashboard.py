"""
Eczaci paneli ana sayfa gorunumu — kendi eczanesine ait ozet metrikler.

KVKK uyumu: Tum sayimlar request.user.eczane uzerinden filtrelenir.
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.analytics.models import OturumLogu, OturumOnerilenEtkenMadde
from apps.campaigns.models import Campaign
from apps.products.models import Kategori

from .models import Kiosk
from .permissions import IsEczaci


HEALTH_OFFLINE_ESIGI_SAN = 15 * 60   # 15 dakika
HEALTH_DEGRADED_ESIGI_SAN = 5 * 60   # 5 dakika


def _kiosk_durum(son_goruldu):
    if son_goruldu is None:
        return "offline"
    yas = (timezone.now() - son_goruldu).total_seconds()
    if yas <= HEALTH_DEGRADED_ESIGI_SAN:
        return "online"
    if yas <= HEALTH_OFFLINE_ESIGI_SAN:
        return "degraded"
    return "offline"


class EczaciDashboardView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsEczaci]

    def get(self, request):
        user = request.user
        eczane = user.eczane
        if eczane is None:
            return Response(
                {
                    "kiosk_sayisi": 0,
                    "kategori_sayisi": 0,
                    "oturum_sayisi": 0,
                    "oturum_sayisi_bugun": 0,
                    "reklam_sayisi": 0,
                    "kiosklar": [],
                    "uyari": "Hesabiniza eczane bagli degil.",
                }
            )

        now = timezone.now()
        bugun_basi = now.replace(hour=0, minute=0, second=0, microsecond=0)

        kiosklar = list(Kiosk.objects.filter(eczane_id=eczane.id).order_by("id"))
        kiosk_ids = [k.id for k in kiosklar]

        oturum_qs = (
            OturumLogu.objects.filter(kiosk_id__in=kiosk_ids)
            if kiosk_ids
            else OturumLogu.objects.none()
        )
        oturum_sayisi = oturum_qs.count()
        oturum_sayisi_bugun = oturum_qs.filter(olusturulma_tarihi__gte=bugun_basi).count()

        # Satış istatistikleri — start_date/end_date parametrelerine duyarlı
        params = request.query_params
        start_date = params.get("start_date")
        end_date = params.get("end_date")

        sold_qs = oturum_qs.filter(sold=True)
        if start_date:
            sold_qs = sold_qs.filter(olusturulma_tarihi__date__gte=start_date)
        if end_date:
            sold_qs = sold_qs.filter(olusturulma_tarihi__date__lte=end_date)
        satis_sayisi = sold_qs.count()

        em_qs = OturumOnerilenEtkenMadde.objects.filter(
            oturum__kiosk_id__in=kiosk_ids, oturum__sold=True
        )
        if start_date:
            em_qs = em_qs.filter(oturum__olusturulma_tarihi__date__gte=start_date)
        if end_date:
            em_qs = em_qs.filter(oturum__olusturulma_tarihi__date__lte=end_date)

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

        # Bu eczaneye hedeflenmis aktif kampanyalar (DOOH v2):
        # target_pharmacies bos (herkese goster) VEYA bu eczane hedefte yer aliyor
        reklam_qs = Campaign.objects.filter(
            status=Campaign.Status.ACTIVE,
            start_date__lte=now,
            end_date__gte=now,
        ).filter(
            Q(target_pharmacies__isnull=True) | Q(target_pharmacies=eczane)
        ).distinct()
        reklam_sayisi = reklam_qs.count()

        kategori_sayisi = Kategori.objects.filter(aktif=True).count()

        kiosklar_payload = [
            {
                "id": k.id,
                "ad":k.ad,
                "mac_adresi": k.mac_adresi,
                "aktif": k.aktif,
                "son_goruldu": k.son_goruldu,
                "durum": _kiosk_durum(k.son_goruldu),
            }
            for k in kiosklar
        ]

        return Response(
            {
                "eczane": {
                    "id": eczane.id,
                    "ad": eczane.ad,
                    "il": eczane.il.ad,
                    "ilce": eczane.ilce.ad,
                },
                "kiosk_sayisi": len(kiosklar),
                "kategori_sayisi": kategori_sayisi,
                "oturum_sayisi": oturum_sayisi,
                "oturum_sayisi_bugun": oturum_sayisi_bugun,
                "reklam_sayisi": reklam_sayisi,
                "kiosklar": kiosklar_payload,
                "satis_sayisi": satis_sayisi,
                "en_cok_satilan_etken_madde": en_cok_satilan,
            }
        )

