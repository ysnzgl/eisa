"""
Blok tipi kayıt defteri (registry).

Kullanım:
    from apps.website.blocks import blok_tipleri_semasi, bloklari_dogrula, blok_verisi_dogrula

`GET /api/website/admin/blok-tipleri/` doğrudan `blok_tipleri_semasi()` çıktısını döner.
Yeni blok tipi eklemek için `tipler.py` içindeki listeye bir `BlokTipi` eklemek yeterlidir;
portal formu şemadan otomatik üretir.
"""
from __future__ import annotations

import re

from .alanlar import Alan, Dogrulayici
from .ikonlar import IKONLAR
from .tipler import BLOK_TIPLERI_LISTESI, BlokTipi

BLOK_TIPLERI: dict[str, BlokTipi] = {t.tip: t for t in BLOK_TIPLERI_LISTESI}

ANCHOR_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
ANCHOR_MAX = 60

__all__ = [
    "Alan",
    "BLOK_TIPLERI",
    "BlokTipi",
    "Dogrulayici",
    "IKONLAR",
    "blok_tipleri_semasi",
    "blok_verisi_dogrula",
    "bloklari_dogrula",
]


def blok_tipleri_semasi() -> list[dict]:
    return [t.sema() for t in BLOK_TIPLERI_LISTESI]


def blok_verisi_dogrula(tip: str, veri, dogrulayici: Dogrulayici | None = None) -> tuple[dict, dict]:
    """Tek bir blok `veri`sini normalize eder → (temiz_veri, hatalar)."""
    blok_tipi = BLOK_TIPLERI.get(tip)
    if blok_tipi is None:
        return {}, {"tip": ["Bilinmeyen blok tipi."]}
    dogrulayici = dogrulayici or Dogrulayici()
    temiz, hatalar = dogrulayici.nesne(blok_tipi.alanlar, veri)
    if blok_tipi.ek_dogrulama:
        blok_tipi.ek_dogrulama(temiz, hatalar)
    return temiz, hatalar


def bloklari_dogrula(bloklar) -> tuple[list[dict], dict]:
    """
    `PUT sayfalar/<id>/bloklar/` gövdesindeki blok dizisini doğrular.

    Girdi öğesi: {id?, tip, veri, gorunur, anchor_id}
    Çıktı: (temiz_liste, hatalar) — hatalar dizi indeksine göre: {"2": {"baslik": [...]}}
    """
    if not isinstance(bloklar, list):
        return [], {"non_field_errors": ["Blok listesi bekleniyor."]}

    dogrulayici = Dogrulayici()
    temiz_liste: list[dict] = []
    hatalar: dict[str, dict] = {}
    gorulen_anchorlar: set[str] = set()

    for i, blok in enumerate(bloklar):
        blok_hatalari: dict = {}
        if not isinstance(blok, dict):
            hatalar[str(i)] = {"non_field_errors": ["Geçersiz blok."]}
            continue

        tip = blok.get("tip")
        veri, veri_hatalari = blok_verisi_dogrula(tip, blok.get("veri") or {}, dogrulayici)
        blok_hatalari.update(veri_hatalari)

        anchor = blok.get("anchor_id") or ""
        if not isinstance(anchor, str):
            anchor = ""
            blok_hatalari["anchor_id"] = ["Geçersiz bölüm kimliği."]
        anchor = anchor.strip().lstrip("#")
        if anchor:
            if len(anchor) > ANCHOR_MAX or not ANCHOR_RE.match(anchor):
                blok_hatalari["anchor_id"] = [
                    "Bölüm kimliği yalnızca küçük harf, rakam, tire ve alt çizgi içerebilir."
                ]
            elif anchor in gorulen_anchorlar:
                blok_hatalari["anchor_id"] = ["Bu bölüm kimliği sayfada zaten kullanılıyor."]
            gorulen_anchorlar.add(anchor)

        gorunur = blok.get("gorunur", True)
        if not isinstance(gorunur, bool):
            blok_hatalari["gorunur"] = ["Doğru/yanlış değeri olmalıdır."]

        blok_id = blok.get("id")
        if isinstance(blok_id, str) and blok_id.startswith("b_"):
            blok_id = blok_id[2:]
        try:
            blok_id = int(blok_id) if blok_id not in (None, "") else None
        except (TypeError, ValueError):
            blok_id = None

        if blok_hatalari:
            hatalar[str(i)] = blok_hatalari
        temiz_liste.append(
            {"id": blok_id, "tip": tip, "veri": veri, "gorunur": gorunur is not False, "anchor_id": anchor}
        )

    return temiz_liste, hatalar
