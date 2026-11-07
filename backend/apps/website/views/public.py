"""
Public API — /api/website/public/ (CONTRACT §3).

  - Yalnızca site sunucusu: X-Website-Token zorunlu (IsWebsiteSunucusu), yoksa 404.
    authentication_classes=[] (panel JWT çerezi / CSRF etkilemez).
  - GET yanıtları (200) `Cache-Control: public, max-age=60`.
  - Site sunucusu tüm istekleri tek pod IP'sinden yaptığı için GET uçlarında throttle YOKTUR;
    yalnızca başvuru POST'u `website_basvuru` scope'u ile IP başına sınırlandırılır.
"""
from __future__ import annotations

import math

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from ..permissions import IsWebsiteSunucusu
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.uow import UnitOfWork

from ..models import Basvuru, BlogKategori, BlogYazisi, Sayfa, SiteAyarlari
from ..serializers import BasvuruPublicSerializer, SiteAyarlariSerializer
from ..services.blog import blog_detay, blog_ozet, public_yazilar
from ..services.medya import medya_referanslarini_tazele
from ..services.menu import menuler
from ..services.sayfa import public_sayfa, tarih
from ..throttles import WebsiteBasvuruThrottle
from ..yardimcilar import istemci_ip, ip_hash

PUBLIC_CACHE_CONTROL = "public, max-age=60"
BLOG_VARSAYILAN_BOYUT = 9
BLOG_MAKS_BOYUT = 24


class _PublicView(APIView):
    authentication_classes: list = []
    permission_classes = [IsWebsiteSunucusu]
    throttle_classes: list = []

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if request.method == "GET" and response.status_code == 200:
            response["Cache-Control"] = PUBLIC_CACHE_CONTROL
        return response


def ayarlar_cikti() -> dict:
    return medya_referanslarini_tazele(SiteAyarlariSerializer(SiteAyarlari.getir()).data)


class PublicSiteView(_PublicView):
    def get(self, request):
        return Response({"ayarlar": ayarlar_cikti(), "menuler": menuler(public=True)})


def _yayindaki_sayfalar():
    return Sayfa.objects.filter(durum=Sayfa.Durum.YAYINDA, aktif_revizyon__isnull=False).select_related("aktif_revizyon")


class PublicSayfalarView(_PublicView):
    def get(self, request):
        return Response(
            [{"slug": s.slug, "guncellenme": tarih(s.aktif_revizyon.yayin_tarihi)} for s in _yayindaki_sayfalar().order_by("sira", "id")]
        )


class PublicSayfaDetayView(_PublicView):
    def get(self, request, slug: str):
        sayfa = _yayindaki_sayfalar().filter(slug=slug).first()
        if sayfa is None:
            return Response({"detail": "Sayfa bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        return Response(public_sayfa(sayfa))


def _pozitif_int(deger, varsayilan: int) -> int:
    try:
        sayi = int(deger)
    except (TypeError, ValueError):
        return varsayilan
    return sayi if sayi > 0 else varsayilan


class PublicBlogListeView(_PublicView):
    def get(self, request):
        params = request.query_params
        sayfa = _pozitif_int(params.get("sayfa"), 1)
        boyut = min(_pozitif_int(params.get("boyut"), BLOG_VARSAYILAN_BOYUT), BLOG_MAKS_BOYUT)

        qs = public_yazilar()
        kategori = (params.get("kategori") or "").strip()
        if kategori:
            qs = qs.filter(kategori__slug=kategori)

        toplam = qs.count()
        bas = (sayfa - 1) * boyut
        sonuclar = [blog_ozet(y) for y in qs[bas : bas + boyut]]

        simdi = timezone.now()
        kategoriler = (
            BlogKategori.objects.annotate(
                yayinda=Count(
                    "yazilar",
                    filter=Q(yazilar__durum=BlogYazisi.Durum.YAYINDA, yazilar__yayin_tarihi__lte=simdi),
                )
            )
            .filter(yayinda__gt=0)
            .order_by("sira", "ad")
        )
        return Response(
            medya_referanslarini_tazele(
                {
                    "sonuclar": sonuclar,
                    "toplam": toplam,
                    "sayfa": sayfa,
                    "sayfa_sayisi": max(1, math.ceil(toplam / boyut)),
                    "kategoriler": [{"ad": k.ad, "slug": k.slug} for k in kategoriler],
                }
            )
        )


class PublicBlogDetayView(_PublicView):
    def get(self, request, slug: str):
        qs = public_yazilar()
        yazi = qs.filter(slug=slug).first()
        if yazi is None:
            return Response({"detail": "Yazı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        return Response(blog_detay(yazi, ilgili_qs=qs))


def kvkk_metin_versiyonu() -> str:
    """Onay anındaki KVKK aydınlatma metninin yayınlanmış revizyonu (ör. 'kvkk-r12')."""
    sayfa = Sayfa.objects.filter(slug="kvkk", durum=Sayfa.Durum.YAYINDA).only("aktif_revizyon_id").first()
    if sayfa is None or not sayfa.aktif_revizyon_id:
        return ""
    return f"kvkk-r{sayfa.aktif_revizyon_id}"


class PublicBasvuruView(_PublicView):
    throttle_classes = [WebsiteBasvuruThrottle]

    def post(self, request):
        veri = request.data if isinstance(request.data, dict) else {}
        # Honeypot: doluysa sessizce "başarılı" dön, kayıt OLUŞTURMA.
        honeypot = veri.get("website")
        if isinstance(honeypot, str) and honeypot.strip():
            return Response({"ok": True}, status=status.HTTP_201_CREATED)

        ser = BasvuruPublicSerializer(data=veri)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        basvuru = Basvuru(
            tip=d["tip"],
            ad_soyad=d["ad_soyad"].strip(),
            kurum=d.get("kurum", "").strip(),
            eposta=d["eposta"].strip(),
            telefon=d.get("telefon", ""),
            il=d.get("il", "").strip(),
            mesaj=d.get("mesaj", "").strip(),
            kvkk_onay=True,
            kvkk_metin_versiyonu=kvkk_metin_versiyonu(),
            kaynak_sayfa=d.get("kaynak_sayfa", ""),
            ip_hash=ip_hash(istemci_ip(request)),
        )
        with UnitOfWork(user=None) as uow:
            uow.add(basvuru)
        return Response({"ok": True}, status=status.HTTP_201_CREATED)
