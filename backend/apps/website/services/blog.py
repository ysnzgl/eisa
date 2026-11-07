"""Blog JSON biçimleri (CONTRACT §3 BlogOzet / detay) ve yardımcılar."""
from __future__ import annotations

import math

from django.utils import timezone

from ..guvenlik import html_duz_metin
from ..models import BlogYazisi
from .medya import medya_referanslarini_tazele
from .sayfa import tarih

OKUMA_HIZI_KELIME_DK = 200


def okuma_suresi_hesapla(icerik_html: str) -> int:
    kelime = len(html_duz_metin(icerik_html).split())
    return max(1, math.ceil(kelime / OKUMA_HIZI_KELIME_DK))


def public_yazilar():
    """Yalnızca durum=yayinda ve yayin_tarihi <= şimdi; sıralama -yayin_tarihi."""
    return (
        BlogYazisi.objects.filter(durum=BlogYazisi.Durum.YAYINDA, yayin_tarihi__lte=timezone.now())
        .select_related("kategori")
        .order_by("-yayin_tarihi", "-id")
    )


def blog_ozet(yazi: BlogYazisi) -> dict:
    return {
        "slug": yazi.slug,
        "baslik": yazi.baslik,
        "ozet": yazi.ozet,
        "kapak": yazi.kapak,
        "kategori": {"ad": yazi.kategori.ad, "slug": yazi.kategori.slug} if yazi.kategori_id else None,
        "etiketler": list(yazi.etiketler or []),
        "yazar_adi": yazi.yazar_adi,
        "yayin_tarihi": tarih(yazi.yayin_tarihi),
        "okuma_suresi": yazi.okuma_suresi,
    }


def blog_detay(yazi: BlogYazisi, *, ilgili_qs=None) -> dict:
    d = blog_ozet(yazi)
    ilgili = []
    if yazi.kategori_id and ilgili_qs is not None:
        ilgili = [blog_ozet(y) for y in ilgili_qs.filter(kategori_id=yazi.kategori_id).exclude(pk=yazi.pk)[:3]]
    d.update(
        {
            "icerik_html": yazi.icerik_html,
            "seo": {
                "baslik": yazi.seo_baslik or yazi.baslik,
                "aciklama": yazi.seo_aciklama or yazi.ozet,
                "og_gorsel": yazi.kapak,
            },
            "ilgili": ilgili,
        }
    )
    return medya_referanslarini_tazele(d)
