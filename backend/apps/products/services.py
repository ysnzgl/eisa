"""Urun domain servisleri.

Kiosk yerel DB'si icin tam katalog payload'i (kategori/soru/cevap/etken madde/
danisma) tek noktada uretilir; kiosk facade `/api/kiosk/v1/catalog/` bu
fonksiyonu kullanir.
"""
from __future__ import annotations

from apps.lookups.models import Cinsiyet, YasAraligi

from .models import Danisma, EtkenMadde, Kategori
from .serializers import (
    DanismaSyncSerializer,
    EtkenMaddeSerializer,
    KategoriSyncSerializer,
)


def build_catalog_payload() -> dict:
    """Kiosk katalog senkronizasyonu icin tam JSON payload."""
    kategoriler = Kategori.objects.filter(aktif=True).select_related(
        "hedef_cinsiyet", "bagli_kategori",
    ).prefetch_related(
        "hedef_yas_araliklari",
        "sorular__cevaplar",
        "sorular__hedef_yas_araliklari",
        "sorular__etken_madde_baglantilari__etken_madde",
    )
    etken_maddeler = EtkenMadde.objects.filter(aktif=True)
    danisma_kategorileri = Danisma.objects.filter(
        aktif=True, ust_kategori__isnull=True
    ).prefetch_related("alt_kategoriler")

    cinsiyetler = list(Cinsiyet.objects.values("id", "kod", "ad").order_by("id"))
    yas_araliklari = list(
        YasAraligi.objects.values("id", "kod", "ad", "alt_sinir", "ust_sinir").order_by("id")
    )

    return {
        "kategoriler": KategoriSyncSerializer(kategoriler, many=True).data,
        "etken_maddeler": EtkenMaddeSerializer(etken_maddeler, many=True).data,
        "danisma_kategorileri": DanismaSyncSerializer(danisma_kategorileri, many=True).data,
        "lookups": {
            "cinsiyetler": cinsiyetler,
            "yas_araliklari": yas_araliklari,
        },
    }
