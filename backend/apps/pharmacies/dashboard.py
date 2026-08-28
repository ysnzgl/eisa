"""
Eczaci paneli ana sayfa gorunumu — kendi eczanesine ait ozet metrikler.

KVKK uyumu: Tum sayimlar request.user.eczane uzerinden filtrelenir.
"""
from datetime import timedelta
from zoneinfo import ZoneInfo

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

from .models import Eczane, Kiosk
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
        istanbul_now = now.astimezone(ZoneInfo("Europe/Istanbul"))
        bugun_basi = istanbul_now.replace(hour=0, minute=0, second=0, microsecond=0)
        yarin_basi = bugun_basi + timedelta(days=1)

        kiosklar = list(Kiosk.objects.filter(eczane_id=eczane.id).order_by("id"))
        kiosk_ids = [k.id for k in kiosklar]

        oturum_qs = OturumLogu.objects.filter(
            Q(eczane_id=eczane.id) | Q(eczane__isnull=True, kiosk__eczane_id=eczane.id)
        )
        oturum_sayisi = oturum_qs.count()
        oturum_sayisi_bugun = oturum_qs.filter(
            olusturulma_tarihi__gte=bugun_basi,
            olusturulma_tarihi__lt=yarin_basi,
        ).count()

        # Satış istatistikleri — start_date/end_date parametrelerine duyarlı
        params = request.query_params
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

        em_qs = OturumOnerilenEtkenMadde.objects.filter(
            Q(oturum__eczane_id=eczane.id)
            | Q(oturum__eczane__isnull=True, oturum__kiosk__eczane_id=eczane.id)
        ).filter(
            oturum__status=OturumLogu.SatisDurumu.SATIS_YAPILDI,
            oturum__result_at__isnull=False,
            satildi=True,
        )
        if start_date:
            em_qs = em_qs.filter(oturum__result_at__date__gte=start_date)
        if end_date:
            em_qs = em_qs.filter(oturum__result_at__date__lte=end_date)

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


class EczaciLeaderboardView(APIView):
    """GET /api/pharmacies/me/leaderboard/

    Eczacının tüm aktif eczaneler arasındaki etkileşim ve satış sıralamasını döndürür.
    Diğer eczanelerin ad/ID bilgisi kesinlikle sızdırılmaz; yalnız sıra ve
    istatistik dönülür.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsEczaci]

    def _collect_scores(self, sales_only=False):
        """Her eczane için oturum sayısını hesaplar (direct + kiosk path)."""
        kw = (
            {"status": OturumLogu.SatisDurumu.SATIS_YAPILDI, "result_at__isnull": False}
            if sales_only
            else {}
        )
        # Oturum.eczane alanı dolu olan kayıtlar
        direct = (
            OturumLogu.objects
            .filter(eczane__isnull=False, eczane__aktif=True, **kw)
            .values("eczane_id")
            .annotate(c=Count("id"))
            .values_list("eczane_id", "c")
        )
        # Oturum.eczane boş; kiosk üzerinden eczane bulunur
        indirect = (
            OturumLogu.objects
            .filter(eczane__isnull=True, kiosk__eczane__aktif=True, **kw)
            .values("kiosk__eczane_id")
            .annotate(c=Count("id"))
            .values_list("kiosk__eczane_id", "c")
        )
        scores: dict[int, int] = {}
        for eid, c in direct:
            if eid is not None:
                scores[eid] = scores.get(eid, 0) + c
        for eid, c in indirect:
            if eid is not None:
                scores[eid] = scores.get(eid, 0) + c
        return scores

    def _rank_info(self, scores: dict, my_id: int) -> dict:
        if not scores:
            return {"sira": 1, "skor": 0, "toplam_eczane": 1, "en_yuksek_skor": 0, "yuzdelik": 100}

        sorted_items = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        en_yuksek = sorted_items[0][1]
        my_score = scores.get(my_id, 0)

        if my_id in scores:
            sira = next(i + 1 for i, (eid, _) in enumerate(sorted_items) if eid == my_id)
            toplam = len(sorted_items)
        else:
            # Hiç aktivitesi olmayan eczane — sonuncu sıra
            sira = len(sorted_items) + 1
            toplam = sira

        yuzdelik = round((toplam - sira) / (toplam - 1) * 100) if toplam > 1 else 100

        return {
            "sira": sira,
            "skor": my_score,
            "toplam_eczane": toplam,
            "en_yuksek_skor": en_yuksek,
            "yuzdelik": max(0, yuzdelik),
        }

    def get(self, request):
        eczane = getattr(request.user, "eczane", None)
        if eczane is None:
            return Response({"etkilesim": None, "satis": None})

        return Response({
            "etkilesim": self._rank_info(self._collect_scores(), eczane.id),
            "satis":     self._rank_info(self._collect_scores(sales_only=True), eczane.id),
        })

