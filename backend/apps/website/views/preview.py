"""
Preview API — /api/website/preview/ (CONTRACT §4).

Token: TimestampSigner(salt="website-preview") ile imzalı "<tur>:<slug>", 1 saat geçerli.
Geçersiz / süresi dolmuş / başka içeriğe ait token → 403. Yanıtlar `Cache-Control: no-store`.
"""
from __future__ import annotations

from urllib.parse import quote, urlencode

from django.conf import settings
from django.core import signing
from rest_framework import status
from ..permissions import IsWebsiteSunucusu
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import BlogYazisi, Sayfa
from ..services.blog import blog_detay, public_yazilar
from ..services.sayfa import onizleme_sayfa

ONIZLEME_SALT = "website-preview"
ONIZLEME_SURESI_SN = 3600


def onizleme_token_uret(tur: str, slug: str) -> str:
    return signing.TimestampSigner(salt=ONIZLEME_SALT).sign(f"{tur}:{slug}")


def onizleme_token_gecerli_mi(token: str, tur: str, slug: str) -> bool:
    if not token:
        return False
    try:
        deger = signing.TimestampSigner(salt=ONIZLEME_SALT).unsign(token, max_age=ONIZLEME_SURESI_SN)
    except signing.BadSignature:  # SignatureExpired da BadSignature'dır
        return False
    return deger == f"{tur}:{slug}"


def onizleme_url(tur: str, slug: str) -> str:
    sorgu = urlencode({"tur": tur, "slug": slug, "token": onizleme_token_uret(tur, slug)}, quote_via=quote)
    return f"{settings.SITE_PUBLIC_URL}/api/preview?{sorgu}"


class _PreviewView(APIView):
    authentication_classes: list = []
    permission_classes = [IsWebsiteSunucusu]
    throttle_classes: list = []
    tur = ""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response

    def token_kontrol(self, request, slug: str):
        if not onizleme_token_gecerli_mi(request.query_params.get("token", ""), self.tur, slug):
            return Response({"detail": "Önizleme bağlantısı geçersiz veya süresi dolmuş."}, status=status.HTTP_403_FORBIDDEN)
        return None


class PreviewSayfaView(_PreviewView):
    tur = "sayfa"

    def get(self, request, slug: str):
        hata = self.token_kontrol(request, slug)
        if hata:
            return hata
        sayfa = Sayfa.objects.select_related("aktif_revizyon").prefetch_related("bloklar").filter(slug=slug).first()
        if sayfa is None:
            return Response({"detail": "Sayfa bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        return Response(onizleme_sayfa(sayfa))


class PreviewBlogView(_PreviewView):
    tur = "blog"

    def get(self, request, slug: str):
        hata = self.token_kontrol(request, slug)
        if hata:
            return hata
        yazi = BlogYazisi.objects.select_related("kategori").filter(slug=slug).first()
        if yazi is None:
            return Response({"detail": "Yazı bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        return Response(blog_detay(yazi, ilgili_qs=public_yazilar()))
