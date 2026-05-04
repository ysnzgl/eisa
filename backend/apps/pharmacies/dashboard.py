"""
Eczaci paneli ana sayfa gorunumu â€” kendi eczanesine ait ozet metrikler.

KVKK uyumu: Tum sayimlar request.user.eczane uzerinden filtrelenir.
"""
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from core_api.cookie_jwt import JWTCookieAuthentication as JWTAuthentication

from apps.analytics.models import OturumLogu
from apps.campaigns.models import Reklam
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

        # Eczanenin il/ilcesine hedeflenmis aktif reklamlar
        reklam_qs = Reklam.objects.filter(
            aktif=True, baslangic_tarihi__lte=now, bitis_tarihi__gte=now
        ).filter(
            Q(hedef_iller__isnull=True) | Q(hedef_iller=eczane.il)
        ).filter(
            Q(hedef_ilceler__isnull=True) | Q(hedef_ilceler=eczane.ilce)
        ).distinct()
        reklam_sayisi = reklam_qs.count()

        kategori_sayisi = Kategori.objects.filter(aktif=True).count()

        kiosklar_payload = [
            {
                "id": k.id,
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
            }
        )

