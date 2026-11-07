"""
Blok alan şeması (CONTRACT §5 "Alan") ve doğrulama/normalizasyon motoru.

Her blok tipinin `veri` nesnesi bir `Alan` listesiyle tanımlanır. Aynı tanım hem
`GET admin/blok-tipleri/` ile portala şema olarak verilir hem de kayıt sırasında
veriyi doğrular:
  - bilinmeyen anahtarlar atılır,
  - eksik / null alanlar varsayılanla doldurulur,
  - metin uzunluğu, sayı aralığı, secim/ikon değerleri, liste adetleri kontrol edilir,
  - Buton href şeması (javascript: vb. reddedilir) kontrol edilir,
  - MediaRef `id`'si DB'de doğrulanır ve diğer alanlar DB'den tazelenir,
  - zengin_metin nh3 ile sanitize edilir.

Hata biçimi DRF ile uyumludur ve iç içe yapıda indekslidir:
    {"kartlar": {"0": {"baslik": ["Bu alan zorunludur."]}}, "butonlar": ["En fazla 3 öğe olabilir."]}
"""
from __future__ import annotations

import copy
import math
from typing import Any, Callable

from ..guvenlik import HREF_HATA_MESAJI, href_gecerli_mi, html_duz_metin, html_temizle
from .ikonlar import IKONLAR, VARSAYILAN_IKON

TURLER = (
    "metin", "uzun_metin", "zengin_metin", "sayi", "bool", "secim",
    "ikon", "medya", "buton", "liste",
)

ZORUNLU_MESAJI = "Bu alan zorunludur."
_YOK = object()

_VARSAYILAN_MAX_UZUNLUK = {"metin": 200, "uzun_metin": 2000, "zengin_metin": 200_000}


class Alan:
    """Tek bir şema alanı. `to_dict()` portalın beklediği CONTRACT §5 biçimini üretir."""

    def __init__(
        self,
        ad: str,
        etiket: str,
        tur: str,
        *,
        zorunlu: bool = False,
        varsayilan: Any = _YOK,
        yardim: str = "",
        max_uzunluk: int | None = None,
        secenekler: list[dict] | None = None,
        min: float | None = None,  # noqa: A002 — sözleşme alan adı
        max: float | None = None,  # noqa: A002
        alanlar: list["Alan"] | None = None,
        min_adet: int | None = None,
        max_adet: int | None = None,
        link: bool = False,
    ) -> None:
        if tur not in TURLER:
            raise ValueError(f"Bilinmeyen alan turu: {tur}")
        self.ad = ad
        self.etiket = etiket
        self.tur = tur
        self.zorunlu = zorunlu
        self.yardim = yardim
        self.max_uzunluk = max_uzunluk if max_uzunluk is not None else _VARSAYILAN_MAX_UZUNLUK.get(tur)
        if tur == "ikon":
            secenekler = [{"deger": i, "etiket": i} for i in IKONLAR]
        self.secenekler = secenekler or []
        self.min = min
        self.max = max
        self.alanlar = alanlar or []
        self.min_adet = min_adet if min_adet is not None else (0 if tur == "liste" else None)
        self.max_adet = max_adet
        # Sadece backend: metin alanı bir bağlantıdır (Buton href / dış URL) → şema kontrolü.
        self.link = link
        self.varsayilan = self._varsayilan_hesapla() if varsayilan is _YOK else varsayilan

    def _varsayilan_hesapla(self):
        if self.tur in ("metin", "uzun_metin", "zengin_metin"):
            return ""
        if self.tur == "sayi":
            return self.min if self.min is not None else 0
        if self.tur == "bool":
            return False
        if self.tur == "secim":
            return self.secenekler[0]["deger"] if self.secenekler else ""
        if self.tur == "ikon":
            return VARSAYILAN_IKON
        if self.tur == "liste":
            return []
        return None  # medya, buton

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "ad": self.ad,
            "etiket": self.etiket,
            "tur": self.tur,
            "zorunlu": self.zorunlu,
            "varsayilan": copy.deepcopy(self.varsayilan),
            "yardim": self.yardim,
        }
        # Opsiyonel anahtarlar yalnızca ilgili tur için (CONTRACT §5).
        if self.tur in ("metin", "uzun_metin", "zengin_metin"):
            d["max_uzunluk"] = self.max_uzunluk
        elif self.tur in ("secim", "ikon"):
            d["secenekler"] = copy.deepcopy(self.secenekler)
        elif self.tur == "sayi":
            d["min"] = self.min
            d["max"] = self.max
        elif self.tur == "liste":
            d["alanlar"] = [a.to_dict() for a in self.alanlar]
            d["min_adet"] = self.min_adet
            d["max_adet"] = self.max_adet
        return d


# Buton nesnesi (CONTRACT §2): {etiket, href, stil}
BUTON_STILLERI = [
    {"deger": "birincil", "etiket": "Birincil"},
    {"deger": "ikincil", "etiket": "İkincil"},
    {"deger": "hayalet", "etiket": "Hayalet"},
]


def buton_alanlari() -> list[Alan]:
    return [
        Alan("etiket", "Etiket", "metin", zorunlu=True, max_uzunluk=60),
        Alan(
            "href", "Bağlantı", "metin", zorunlu=True, max_uzunluk=500, link=True,
            yardim="'/sayfa', '/#bolum', '#bolum', 'https://...', 'mailto:...' veya 'tel:...'",
        ),
        Alan("stil", "Stil", "secim", zorunlu=True, secenekler=BUTON_STILLERI),
    ]


class Dogrulayici:
    """Bir istek boyunca medya sorgularını önbellekleyen doğrulama bağlamı."""

    def __init__(self) -> None:
        self._medya_onbellek: dict[int, Any] = {}

    # ── Medya ──────────────────────────────────────────────────────────────
    def medya_getir(self, medya_id: int):
        from ..models import WebsiteMedya

        if medya_id not in self._medya_onbellek:
            self._medya_onbellek[medya_id] = WebsiteMedya.objects.filter(pk=medya_id).first()
        return self._medya_onbellek[medya_id]

    def medya_ref(self, deger, *, zorunlu: bool = False):
        """MediaRef|null doğrular; (temiz, hata) döner. Temiz değer DB'den tazelenir."""
        if deger in (None, "", {}):
            return None, ([ZORUNLU_MESAJI] if zorunlu else None)
        if isinstance(deger, dict):
            ham_id = deger.get("id")
        else:
            ham_id = deger
        if isinstance(ham_id, bool):
            ham_id = None
        try:
            medya_id = int(ham_id)
        except (TypeError, ValueError):
            return None, ["Geçersiz medya referansı."]
        medya = self.medya_getir(medya_id)
        if medya is None:
            return None, ["Medya bulunamadı."]
        return medya.media_ref(), None

    # ── Nesne / alan ──────────────────────────────────────────────────────
    def nesne(self, alanlar: list[Alan], veri) -> tuple[dict, dict]:
        """Bir nesneyi alan listesine göre normalize eder. Bilinmeyen anahtarlar atılır."""
        if not isinstance(veri, dict):
            veri = {}
        temiz: dict[str, Any] = {}
        hatalar: dict[str, Any] = {}
        for alan in alanlar:
            deger, hata = self.alan(alan, veri.get(alan.ad))
            temiz[alan.ad] = deger
            if hata:
                hatalar[alan.ad] = hata
        return temiz, hatalar

    def alan(self, alan: Alan, deger):
        if deger is None:
            deger = copy.deepcopy(alan.varsayilan)
        yontem: Callable = getattr(self, f"_tur_{alan.tur}")
        return yontem(alan, deger)

    # ── Tür doğrulayıcıları: (temiz_deger, hata|None) ──────────────────────
    def _metin_ortak(self, alan: Alan, deger, *, cok_satir: bool):
        if isinstance(deger, bool) or not isinstance(deger, (str, int, float)):
            return copy.deepcopy(alan.varsayilan), ["Metin olmalıdır."]
        deger = str(deger).replace("\r\n", "\n").replace("\r", "\n").strip()
        if not cok_satir:
            deger = " ".join(deger.split("\n"))
        if alan.zorunlu and not deger:
            return deger, [ZORUNLU_MESAJI]
        if alan.max_uzunluk and len(deger) > alan.max_uzunluk:
            return deger, [f"En fazla {alan.max_uzunluk} karakter olabilir."]
        if alan.link and deger and not href_gecerli_mi(deger):
            return deger, [HREF_HATA_MESAJI]
        return deger, None

    def _tur_metin(self, alan, deger):
        return self._metin_ortak(alan, deger, cok_satir=False)

    def _tur_uzun_metin(self, alan, deger):
        return self._metin_ortak(alan, deger, cok_satir=True)

    def _tur_zengin_metin(self, alan, deger):
        if not isinstance(deger, str):
            return "", ["Metin olmalıdır."]
        temiz = html_temizle(deger)
        if alan.zorunlu and not html_duz_metin(temiz) and "<img" not in temiz:
            return temiz, [ZORUNLU_MESAJI]
        if alan.max_uzunluk and len(temiz) > alan.max_uzunluk:
            return temiz, [f"En fazla {alan.max_uzunluk} karakter olabilir."]
        return temiz, None

    def _tur_sayi(self, alan, deger):
        if isinstance(deger, bool):
            return alan.varsayilan, ["Sayı olmalıdır."]
        if isinstance(deger, str):
            try:
                deger = float(deger.strip().replace(",", "."))
            except ValueError:
                return alan.varsayilan, ["Sayı olmalıdır."]
        if not isinstance(deger, (int, float)) or (isinstance(deger, float) and not math.isfinite(deger)):
            return alan.varsayilan, ["Sayı olmalıdır."]
        if isinstance(deger, float) and deger.is_integer():
            deger = int(deger)
        if alan.min is not None and deger < alan.min:
            return deger, [f"En az {alan.min} olabilir."]
        if alan.max is not None and deger > alan.max:
            return deger, [f"En fazla {alan.max} olabilir."]
        return deger, None

    def _tur_bool(self, alan, deger):
        if isinstance(deger, bool):
            return deger, None
        if isinstance(deger, str) and deger.lower() in ("true", "false"):
            return deger.lower() == "true", None
        return alan.varsayilan, ["Doğru/yanlış değeri olmalıdır."]

    def _secim_ortak(self, alan, deger, mesaj):
        for secenek in alan.secenekler:
            if str(secenek["deger"]) == str(deger):
                return secenek["deger"], None
        return alan.varsayilan, [mesaj]

    def _tur_secim(self, alan, deger):
        return self._secim_ortak(alan, deger, "Geçersiz seçim.")

    def _tur_ikon(self, alan, deger):
        return self._secim_ortak(alan, deger, "Geçersiz ikon.")

    def _tur_medya(self, alan, deger):
        return self.medya_ref(deger, zorunlu=alan.zorunlu)

    def _tur_buton(self, alan, deger):
        if deger in (None, {}):
            return None, ([ZORUNLU_MESAJI] if alan.zorunlu else None)
        if not isinstance(deger, dict):
            return None, ["Geçersiz buton."]
        temiz, hatalar = self.nesne(buton_alanlari(), deger)
        return temiz, (hatalar or None)

    def _tur_liste(self, alan, deger):
        if not isinstance(deger, list):
            return [], ["Liste olmalıdır."]
        temiz_liste: list = []
        oge_hatalari: dict[str, Any] = {}
        for i, oge in enumerate(deger):
            if not isinstance(oge, dict):
                oge_hatalari[str(i)] = {"non_field_errors": ["Geçersiz öğe."]}
                temiz_liste.append({})
                continue
            temiz, hatalar = self.nesne(alan.alanlar, oge)
            temiz_liste.append(temiz)
            if hatalar:
                oge_hatalari[str(i)] = hatalar
        if alan.min_adet is not None and len(deger) < alan.min_adet:
            return temiz_liste, [f"En az {alan.min_adet} öğe olmalıdır."]
        if alan.max_adet is not None and len(deger) > alan.max_adet:
            return temiz_liste, [f"En fazla {alan.max_adet} öğe olabilir."]
        return temiz_liste, (oge_hatalari or None)
