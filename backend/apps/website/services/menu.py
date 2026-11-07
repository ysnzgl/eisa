"""
Menü servisleri (CONTRACT §3 MenuItem, §5 Menüler).

`href` çözümü:
  sayfa → /slug   (anasayfa → /)
  bolum → /slug#anchor   (anasayfa → /#anchor)
  blog  → /blog
  dis   → url olduğu gibi
Public yanıtta yalnızca aktif öğeler gelir; yayında olmayan sayfaya bağlı öğe (ve alt
öğeleri) dahil edilmez.
"""
from __future__ import annotations

from apps.core.uow import UnitOfWork

from ..blocks import ANCHOR_MAX, ANCHOR_RE
from ..guvenlik import HREF_HATA_MESAJI, href_gecerli_mi
from ..models import Menu, MenuOgesi, Sayfa
from .revalidate import revalidate

KONUMLAR = [k for k, _ in Menu.Konum.choices]
LINK_TIPLERI = [k for k, _ in MenuOgesi.LinkTipi.choices]
ETIKET_MAX = 100


def href_coz(link_tipi: str, sayfa: Sayfa | None, bolum_anchor: str, url: str) -> str:
    if link_tipi == MenuOgesi.LinkTipi.BLOG:
        return "/blog"
    if link_tipi == MenuOgesi.LinkTipi.DIS:
        return url or ""
    if sayfa is None:
        return ""
    taban = "/" if sayfa.slug == "anasayfa" else f"/{sayfa.slug}"
    if link_tipi == MenuOgesi.LinkTipi.BOLUM:
        return f"{taban}#{bolum_anchor}"
    return taban


def _oge_href(oge: MenuOgesi) -> str:
    return href_coz(oge.link_tipi, oge.sayfa, oge.bolum_anchor, oge.url)


def _public_gorunur_mu(oge: MenuOgesi) -> bool:
    if not oge.aktif:
        return False
    if oge.link_tipi in (MenuOgesi.LinkTipi.SAYFA, MenuOgesi.LinkTipi.BOLUM):
        return oge.sayfa is not None and oge.sayfa.durum == Sayfa.Durum.YAYINDA
    return True


def _agac(ogeler: list[MenuOgesi], *, public: bool) -> list[dict]:
    cocuklar: dict[int, list[MenuOgesi]] = {}
    kokler: list[MenuOgesi] = []
    for oge in ogeler:
        if oge.ust_id is None:
            kokler.append(oge)
        else:
            cocuklar.setdefault(oge.ust_id, []).append(oge)

    def dugum(oge: MenuOgesi, seviye: int) -> dict | None:
        if public and not _public_gorunur_mu(oge):
            return None
        alt = []
        if seviye == 0:
            for c in cocuklar.get(oge.pk, []):
                d = dugum(c, 1)
                if d is not None:
                    alt.append(d)
        if public:
            return {
                "id": oge.pk,
                "etiket": oge.etiket,
                "href": _oge_href(oge),
                "yeni_sekme": oge.yeni_sekme,
                "cta": oge.cta,
                "cocuklar": alt,
            }
        return {
            "id": oge.pk,
            "etiket": oge.etiket,
            "link_tipi": oge.link_tipi,
            "sayfa_id": oge.sayfa_id,
            "bolum_anchor": oge.bolum_anchor,
            "url": oge.url,
            "yeni_sekme": oge.yeni_sekme,
            "cta": oge.cta,
            "aktif": oge.aktif,
            "href": _oge_href(oge),
            "cocuklar": alt,
        }

    sonuc = []
    for k in kokler:
        d = dugum(k, 0)
        if d is not None:
            sonuc.append(d)
    return sonuc


def menuler(*, public: bool) -> dict:
    ogeler_by_konum: dict[str, list[MenuOgesi]] = {k: [] for k in KONUMLAR}
    qs = MenuOgesi.objects.select_related("menu", "sayfa").order_by("sira", "id")
    for oge in qs:
        ogeler_by_konum.setdefault(oge.menu.konum, []).append(oge)
    return {k: _agac(v, public=public) for k, v in ogeler_by_konum.items()}


def menu_agaci(konum: str, *, public: bool) -> list[dict]:
    qs = MenuOgesi.objects.filter(menu__konum=konum).select_related("sayfa").order_by("sira", "id")
    return _agac(list(qs), public=public)


# ── PUT menuler/<konum>/ doğrulama ──────────────────────────────────────────


def _bool(deger, varsayilan: bool, ad: str, hatalar: dict) -> bool:
    if deger is None:
        return varsayilan
    if isinstance(deger, bool):
        return deger
    hatalar[ad] = ["Doğru/yanlış değeri olmalıdır."]
    return varsayilan


def _oge_dogrula(girdi, seviye: int, sayfalar: dict[int, Sayfa]) -> tuple[dict, dict]:
    hatalar: dict = {}
    if not isinstance(girdi, dict):
        return {}, {"non_field_errors": ["Geçersiz menü öğesi."]}

    etiket = girdi.get("etiket")
    etiket = etiket.strip() if isinstance(etiket, str) else ""
    if not etiket:
        hatalar["etiket"] = ["Bu alan zorunludur."]
    elif len(etiket) > ETIKET_MAX:
        hatalar["etiket"] = [f"En fazla {ETIKET_MAX} karakter olabilir."]

    link_tipi = girdi.get("link_tipi")
    if link_tipi not in LINK_TIPLERI:
        hatalar["link_tipi"] = ["Geçersiz bağlantı tipi."]

    sayfa_id = None
    bolum_anchor = ""
    url = ""
    if link_tipi in (MenuOgesi.LinkTipi.SAYFA, MenuOgesi.LinkTipi.BOLUM):
        ham = girdi.get("sayfa_id")
        try:
            sayfa_id = int(ham) if ham not in (None, "") and not isinstance(ham, bool) else None
        except (TypeError, ValueError):
            sayfa_id = None
        if sayfa_id is None:
            hatalar["sayfa_id"] = ["Bu alan zorunludur."]
        elif sayfa_id not in sayfalar:
            hatalar["sayfa_id"] = ["Sayfa bulunamadı."]
    if link_tipi == MenuOgesi.LinkTipi.BOLUM:
        bolum_anchor = girdi.get("bolum_anchor")
        bolum_anchor = bolum_anchor.strip().lstrip("#") if isinstance(bolum_anchor, str) else ""
        if not bolum_anchor:
            hatalar["bolum_anchor"] = ["Bu alan zorunludur."]
        elif len(bolum_anchor) > ANCHOR_MAX or not ANCHOR_RE.match(bolum_anchor):
            hatalar["bolum_anchor"] = ["Bölüm kimliği yalnızca küçük harf, rakam, tire ve alt çizgi içerebilir."]
    if link_tipi == MenuOgesi.LinkTipi.DIS:
        url = girdi.get("url")
        url = url.strip() if isinstance(url, str) else ""
        if not url:
            hatalar["url"] = ["Bu alan zorunludur."]
        elif not href_gecerli_mi(url):
            hatalar["url"] = [HREF_HATA_MESAJI]

    yeni_sekme = _bool(girdi.get("yeni_sekme"), False, "yeni_sekme", hatalar)
    cta = _bool(girdi.get("cta"), False, "cta", hatalar)
    aktif = _bool(girdi.get("aktif"), True, "aktif", hatalar)

    ham_id = girdi.get("id")
    try:
        oge_id = int(ham_id) if ham_id not in (None, "") and not isinstance(ham_id, bool) else None
    except (TypeError, ValueError):
        oge_id = None

    cocuklar_girdi = girdi.get("cocuklar") or []
    temiz_cocuklar: list[dict] = []
    if not isinstance(cocuklar_girdi, list):
        hatalar["cocuklar"] = ["Liste olmalıdır."]
    elif cocuklar_girdi and seviye >= 1:
        hatalar["cocuklar"] = ["Menü en fazla 2 seviyeli olabilir."]
    else:
        cocuk_hatalari = {}
        for j, c in enumerate(cocuklar_girdi):
            temiz_c, h = _oge_dogrula(c, seviye + 1, sayfalar)
            temiz_cocuklar.append(temiz_c)
            if h:
                cocuk_hatalari[str(j)] = h
        if cocuk_hatalari:
            hatalar["cocuklar"] = cocuk_hatalari

    return (
        {
            "id": oge_id,
            "etiket": etiket,
            "link_tipi": link_tipi,
            "sayfa_id": sayfa_id,
            "bolum_anchor": bolum_anchor,
            "url": url,
            "yeni_sekme": yeni_sekme,
            "cta": cta,
            "aktif": aktif,
            "cocuklar": temiz_cocuklar,
        },
        hatalar,
    )


def menu_dogrula(govde) -> tuple[list[dict], dict]:
    """Hata biçimi kök dizi indeksine göre: {"0": {"cocuklar": {"1": {"url": [...]}}}}"""
    if not isinstance(govde, list):
        return [], {"non_field_errors": ["Menü öğeleri dizisi bekleniyor."]}
    sayfalar = {s.pk: s for s in Sayfa.objects.all()}
    temiz, hatalar = [], {}
    for i, g in enumerate(govde):
        t, h = _oge_dogrula(g, 0, sayfalar)
        temiz.append(t)
        if h:
            hatalar[str(i)] = h
    return temiz, hatalar


def menu_kaydet(konum: str, temiz_ogeler: list[dict], *, user, revalidate_et: bool = True) -> None:
    """Konumdaki ağacı atomik olarak değiştirir. Bilinen `id`'ler güncellenir, kalanlar silinir."""
    with UnitOfWork(user=user) as uow:
        menu = Menu.objects.filter(konum=konum).first()
        if menu is None:
            menu = uow.add(Menu(konum=konum))
        mevcut = {o.pk: o for o in MenuOgesi.objects.filter(menu=menu)}
        kullanilan: set[int] = set()

        def kaydet(girdi: dict, ust: MenuOgesi | None, sira: int) -> None:
            oge = mevcut.get(girdi["id"]) if girdi["id"] not in kullanilan else None
            alanlar = {
                "etiket": girdi["etiket"],
                "link_tipi": girdi["link_tipi"],
                "sayfa_id": girdi["sayfa_id"],
                "bolum_anchor": girdi["bolum_anchor"],
                "url": girdi["url"],
                "yeni_sekme": girdi["yeni_sekme"],
                "cta": girdi["cta"],
                "aktif": girdi["aktif"],
                "sira": sira,
                "ust": ust,
            }
            if oge is not None:
                for k, v in alanlar.items():
                    setattr(oge, k, v)
                uow.update(oge)
            else:
                oge = uow.add(MenuOgesi(menu=menu, **alanlar))
            kullanilan.add(oge.pk)
            for j, c in enumerate(girdi["cocuklar"]):
                kaydet(c, oge, j)

        for i, g in enumerate(temiz_ogeler):
            kaydet(g, None, i)
        MenuOgesi.objects.filter(menu=menu).exclude(pk__in=kullanilan).delete()
        if revalidate_et:
            revalidate("site")
