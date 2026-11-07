"""
Web sitesi yönetimi — içerik araması (portal "Sitede ara").

Taslak içerik (editörün düzenlediği hâl) taranır: sayfa başlık/SEO, blok alanları (iç içe listeler
ve sayılar dahil, şema üzerinden okunabilir konum etiketiyle), blog yazıları ve kategorileri, menü
öğeleri, site ayarları ve medya kütüphanesi (alternatif metin, dosya adı). Eski yayın revizyonları
(geçmiş) ve başvurular (kişisel veri) içerik olmadığından taranmaz.

Eşleştirme Türkçe'ye duyarlı, büyük/küçük harf ve aksan bağımsızdır ("saglik" → "SAĞLIK").
Normalizasyon karakter sayısını korur; böylece eşleşme konumu orijinal metinde de geçerlidir.
"""
from __future__ import annotations

import html
import re
from typing import Iterator

from ..blocks import BLOK_TIPLERI, Alan
from ..blocks.alanlar import buton_alanlari
from ..models import BlogKategori, BlogYazisi, MenuOgesi, Sayfa, SiteAyarlari, WebsiteMedya

MIN_UZUNLUK = 2
MAX_UZUNLUK = 100
MAX_SONUC = 200
BAGLAM = 60  # eşleşmenin önünde/arkasında gösterilecek karakter

_KATLA = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"})
_ETIKET_RE = re.compile(r"<[^>]+>")
_BOSLUK_RE = re.compile(r"\s+")

SAYFA_ALANLARI = [("baslik", "Sayfa başlığı"), ("slug", "Adres"), ("seo_baslik", "SEO başlığı"), ("seo_aciklama", "SEO açıklaması")]
BLOG_ALANLARI = [
    ("baslik", "Başlık"), ("slug", "Adres"), ("ozet", "Özet"), ("icerik_html", "İçerik"),
    ("yazar_adi", "Yazar"), ("seo_baslik", "SEO başlığı"), ("seo_aciklama", "SEO açıklaması"),
]
AYAR_ALANLARI = [
    ("site_adi", "Site adı"), ("seo_baslik_sablonu", "SEO başlık şablonu"), ("seo_aciklama", "Varsayılan SEO açıklaması"),
    ("firma_unvani", "Firma unvanı"), ("eposta", "E-posta"), ("telefon", "Telefon"), ("whatsapp", "WhatsApp"),
    ("adres", "Adres"), ("footer_aciklama", "Footer açıklaması"),
]
MENU_KONUM_ADLARI = {"header": "Üst menü", "footer": "Alt menü", "footer_alt": "Yasal bağlantılar"}


def normalize(metin: str) -> str:
    """Türkçe küçük harf + aksan katlama; uzunluk korunur (karakter başına 1 karakter)."""
    parcalar = []
    for c in metin:
        if c == "İ":
            c = "i"
        elif c == "I":
            c = "ı"
        else:
            k = c.lower()
            c = k if len(k) == 1 else c
        parcalar.append(c)
    return "".join(parcalar).translate(_KATLA)


def html_metne(deger: str) -> str:
    """Zengin metni düz metne çevirir (etiketler boşluk olur, varlıklar çözülür)."""
    return _BOSLUK_RE.sub(" ", html.unescape(_ETIKET_RE.sub(" ", deger or ""))).strip()


def parca_uret(metin: str, igne: str) -> dict | None:
    """Metinde ilk eşleşme çevresinden güvenli parça üretir: {onceki, eslesen, sonraki, adet}."""
    if not metin:
        return None
    n = normalize(metin)
    i = n.find(igne)
    if i < 0:
        return None
    j = i + len(igne)
    bas, son = max(0, i - BAGLAM), min(len(metin), j + BAGLAM)
    return {
        "onceki": ("…" if bas > 0 else "") + metin[bas:i],
        "eslesen": metin[i:j],
        "sonraki": metin[j:son] + ("…" if son < len(metin) else ""),
        "adet": n.count(igne),
    }


def _sayi_metinleri(deger) -> tuple[str, ...]:
    """Sayıyı sitede göründüğü (18.000 / 3,5) ve ham (18000 / 3.5) biçimleriyle döner."""
    if isinstance(deger, bool):
        return ()
    if isinstance(deger, float) and deger.is_integer():
        deger = int(deger)
    if isinstance(deger, int):
        bicimli = f"{deger:,}".replace(",", ".")
    else:
        bicimli = str(deger).replace(".", ",")
    ham = str(deger)
    return (bicimli,) if bicimli == ham else (bicimli, ham)


def _blok_alanlari(alanlar: list[Alan], veri, yol: str, konum: list[str]) -> Iterator[tuple[str, list[str], str | tuple[str, ...]]]:
    """Şemaya göre bloğun aranabilir metinlerini (veri yolu, konum etiketleri, metin[ler]) üretir."""
    if not isinstance(veri, dict):
        return
    for alan in alanlar:
        deger = veri.get(alan.ad)
        if deger in (None, "", [], {}):
            continue
        alan_yolu = f"{yol}.{alan.ad}" if yol else alan.ad
        etiketler = [*konum, alan.etiket]
        if alan.tur in ("metin", "uzun_metin") and isinstance(deger, str):
            yield alan_yolu, etiketler, deger
        elif alan.tur == "zengin_metin" and isinstance(deger, str):
            yield alan_yolu, etiketler, html_metne(deger)
        elif alan.tur == "sayi" and isinstance(deger, (int, float)):
            metinler = _sayi_metinleri(deger)
            if metinler:
                yield alan_yolu, etiketler, metinler
        elif alan.tur == "buton":
            yield from _blok_alanlari(buton_alanlari(), deger, alan_yolu, etiketler)
        elif alan.tur == "liste" and isinstance(deger, list):
            for i, oge in enumerate(deger):
                yield from _blok_alanlari(alan.alanlar, oge, f"{alan_yolu}.{i}", [*etiketler, f"{i + 1}. öğe"])


def ara(sorgu: str) -> dict:
    sorgu = (sorgu or "").strip()[:MAX_UZUNLUK]
    sonuc = {"q": sorgu, "toplam": 0, "kesildi": False, "sonuclar": []}
    if len(sorgu) < MIN_UZUNLUK:
        return sonuc
    igne = normalize(sorgu)
    liste = sonuc["sonuclar"]

    def ekle(kayit: dict, metin: str | tuple[str, ...]) -> None:
        # Birden çok biçim verilebilir (ör. sayı: "18.000" ve "18000"); ilk eşleşen kullanılır.
        parca = next((p for m in (metin if isinstance(metin, tuple) else (metin,)) if (p := parca_uret(m, igne))), None)
        if parca is None:
            return
        sonuc["toplam"] += 1
        if len(liste) >= MAX_SONUC:
            sonuc["kesildi"] = True
            return
        kayit["parca"] = {k: parca[k] for k in ("onceki", "eslesen", "sonraki")}
        kayit["adet"] = parca["adet"]
        liste.append(kayit)

    # ── Sayfalar + bloklar (taslak) ─────────────────────────────────────────
    for sayfa in Sayfa.objects.prefetch_related("bloklar").order_by("sira", "baslik"):
        grup = {"tur": "sayfa", "id": sayfa.pk, "baslik": sayfa.baslik, "slug": sayfa.slug, "durum": sayfa.durum}
        for alan, etiket in SAYFA_ALANLARI:
            ekle(
                {"grup": grup, "konum": ["Sayfa ve SEO ayarları", etiket], "hedef": {"ekran": "sayfa", "sayfa_id": sayfa.pk, "alan": f"meta:{alan}"}},
                getattr(sayfa, alan) or "",
            )
        for blok in sorted(sayfa.bloklar.all(), key=lambda b: b.sira):
            tip = BLOK_TIPLERI.get(blok.tip)
            blok_adi = tip.ad if tip else blok.tip
            ortak = {"grup": grup, "blok": {"id": blok.pk, "tip": blok.tip, "ad": blok_adi, "sira": blok.sira + 1, "gizli": not blok.gorunur}}
            if blok.anchor_id:
                ekle({**ortak, "konum": [blok_adi, "Bölüm bağlantısı (anchor)"],
                      "hedef": {"ekran": "sayfa", "sayfa_id": sayfa.pk, "blok_id": blok.pk, "alan": "anchor_id"}}, blok.anchor_id)
            if tip is None:
                continue
            for alan_yolu, etiketler, metin in _blok_alanlari(tip.alanlar, blok.veri, "", []):
                ekle({**ortak, "konum": [blok_adi, *etiketler],
                      "hedef": {"ekran": "sayfa", "sayfa_id": sayfa.pk, "blok_id": blok.pk, "alan": alan_yolu}}, metin)

    # ── Blog ────────────────────────────────────────────────────────────────
    for yazi in BlogYazisi.objects.order_by("-yayin_tarihi", "-pk"):
        grup = {"tur": "blog", "id": yazi.pk, "baslik": yazi.baslik, "slug": yazi.slug, "durum": yazi.durum}
        for alan, etiket in BLOG_ALANLARI:
            deger = getattr(yazi, alan) or ""
            ekle({"grup": grup, "konum": [etiket], "hedef": {"ekran": "blog", "yazi_id": yazi.pk, "alan": alan}},
                 html_metne(deger) if alan == "icerik_html" else deger)
        if yazi.etiketler:
            ekle({"grup": grup, "konum": ["Etiketler"], "hedef": {"ekran": "blog", "yazi_id": yazi.pk, "alan": "etiketler"}},
                 ", ".join(str(e) for e in yazi.etiketler))

    # ── Blog kategorileri ───────────────────────────────────────────────────
    for kategori in BlogKategori.objects.order_by("sira", "ad"):
        grup = {"tur": "blog_kategori", "id": kategori.pk, "baslik": "Blog kategorileri"}
        for alan, etiket in (("ad", "Kategori adı"), ("slug", "Kategori adresi")):
            ekle({"grup": grup, "konum": [kategori.ad, etiket], "hedef": {"ekran": "blog_kategori", "kategori_id": kategori.pk, "alan": alan}},
                 getattr(kategori, alan) or "")

    # ── Menüler ─────────────────────────────────────────────────────────────
    for oge in MenuOgesi.objects.select_related("menu", "ust").order_by("menu__konum", "sira"):
        konum = oge.menu.konum
        grup = {"tur": "menu", "id": konum, "baslik": MENU_KONUM_ADLARI.get(konum, konum)}
        yol = [oge.ust.etiket, oge.etiket] if oge.ust_id else [oge.etiket]
        for alan, etiket, deger in (("etiket", "Etiket", oge.etiket), ("url", "Bağlantı", oge.url), ("bolum_anchor", "Bölüm", oge.bolum_anchor)):
            ekle({"grup": grup, "konum": [*yol, etiket], "hedef": {"ekran": "menu", "konum": konum, "oge_id": oge.pk, "alan": alan}}, deger or "")

    # ── Site ayarları ───────────────────────────────────────────────────────
    ayarlar = SiteAyarlari.objects.first()
    if ayarlar:
        grup = {"tur": "ayarlar", "id": ayarlar.pk, "baslik": "Site Ayarları"}
        for alan, etiket in AYAR_ALANLARI:
            ekle({"grup": grup, "konum": [etiket], "hedef": {"ekran": "ayarlar", "alan": alan}}, getattr(ayarlar, alan) or "")
        for i, link in enumerate(ayarlar.sosyal_linkler or []):
            if isinstance(link, dict):
                ekle({"grup": grup, "konum": ["Sosyal bağlantılar", f"{i + 1}. bağlantı"], "hedef": {"ekran": "ayarlar", "alan": "sosyal_linkler"}},
                     f"{link.get('platform', '')} {link.get('url', '')}".strip())

    # ── Medya kütüphanesi ───────────────────────────────────────────────────
    for medya in WebsiteMedya.objects.order_by("-olusturulma_tarihi", "-pk"):
        grup = {"tur": "medya", "id": "medya", "baslik": "Medya kütüphanesi"}
        ad = medya.dosya_adi or f"Görsel #{medya.pk}"
        for alan, etiket in (("alt", "Alternatif metin"), ("dosya_adi", "Dosya adı")):
            ekle({"grup": grup, "konum": [ad, etiket], "hedef": {"ekran": "medya", "medya_id": medya.pk, "alan": alan}},
                 getattr(medya, alan) or "")

    return sonuc
