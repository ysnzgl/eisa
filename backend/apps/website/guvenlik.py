"""
Web sitesi içerik güvenliği: link (href) doğrulama ve HTML sanitize (nh3).

Sözleşme: CONTRACT §2 (Buton href şemaları) ve §5 Blog (izinli etiketler).
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

import nh3

# ── Link doğrulama ──────────────────────────────────────────────────────────

HREF_MAX_UZUNLUK = 500
_KONTROL_KARAKTERI = re.compile(r"[\x00-\x20\x7f\\]")
_TEL_RE = re.compile(r"^tel:\+?[0-9()\-]{3,30}$")
_MAILTO_RE = re.compile(r"^mailto:[^\s@]+@[^\s@]+$")
_ANCHOR_RE = re.compile(r"^#[A-Za-z0-9][A-Za-z0-9_\-]*$")

HREF_HATA_MESAJI = (
    "Geçersiz bağlantı. '/' ile başlayan iç yol, '#bolum', 'https://', 'mailto:' veya 'tel:' kullanın."
)


def href_gecerli_mi(href: str) -> bool:
    """CONTRACT §2: iç yol (/...), #anchor, https://, mailto:, tel: (wa.me https altında)."""
    if not isinstance(href, str) or not href or len(href) > HREF_MAX_UZUNLUK:
        return False
    # Boşluk, kontrol karakteri ve ters bölü (tarayıcılar "/\\evil" → "//evil" yorumlar) yasak.
    if _KONTROL_KARAKTERI.search(href):
        return False
    if href.startswith("/"):
        # Protokol-göreli "//evil.com" dış bağlantıdır; iç yol sayılmaz.
        return not href.startswith("//")
    if href.startswith("#"):
        return bool(_ANCHOR_RE.match(href))
    lower = href.lower()
    if lower.startswith("https://"):
        try:
            parts = urlsplit(href)
        except ValueError:
            return False
        return bool(parts.netloc) and "@" not in parts.netloc
    if lower.startswith("mailto:"):
        return bool(_MAILTO_RE.match(href))
    if lower.startswith("tel:"):
        return bool(_TEL_RE.match(href))
    return False


# ── HTML sanitize ───────────────────────────────────────────────────────────

IZINLI_ETIKETLER = {
    "p", "h2", "h3", "h4", "ul", "ol", "li", "strong", "em", "u", "s", "a",
    "blockquote", "br", "hr", "code", "pre", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td",
}
# `rel` nh3 tarafından link_rel ile zorla eklenir; izinli öznitelik listesinde olmamalıdır.
IZINLI_OZNITELIKLER = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "width", "height"},
}
IZINLI_URL_SEMALARI = {"https", "mailto", "tel"}
MEDYA_YOL_ONEKI = "/api/media/website/"
_SAYI_RE = re.compile(r"^\d{1,5}$")


def _oznitelik_filtresi(etiket: str, oznitelik: str, deger: str):
    if etiket == "img" and oznitelik == "src":
        # Yalnızca kendi medya yolumuz. Tam URL gelirse (portal editörü API_BASE ekleyebilir)
        # host atılır ve göreli yola indirgenir; host'a hiçbir şekilde güvenilmez.
        if deger.startswith(MEDYA_YOL_ONEKI):
            return deger if ".." not in deger else None
        try:
            parts = urlsplit(deger)
        except ValueError:
            return None
        if parts.scheme in ("http", "https") and parts.path.startswith(MEDYA_YOL_ONEKI) and ".." not in parts.path:
            return parts.path
        return None
    if etiket == "img" and oznitelik in ("width", "height"):
        return deger if _SAYI_RE.match(deger or "") else None
    if etiket == "a" and oznitelik == "target":
        return deger if deger in ("_blank", "_self") else None
    if etiket == "a" and oznitelik == "href":
        return deger if href_gecerli_mi(deger) else None
    return deger


def html_temizle(html: str) -> str:
    """Zengin metni CONTRACT §5'teki izinli etiket/öznitelik kümesine indirger."""
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=IZINLI_ETIKETLER,
        clean_content_tags={"script", "style"},
        attributes=IZINLI_OZNITELIKLER,
        attribute_filter=_oznitelik_filtresi,
        url_schemes=IZINLI_URL_SEMALARI,
        link_rel="noopener noreferrer",
        strip_comments=True,
    ).strip()


def html_duz_metin(html: str) -> str:
    """HTML'den etiketsiz düz metin (okuma süresi / boşluk kontrolü için)."""
    if not html:
        return ""
    text = nh3.clean(html, tags=set(), clean_content_tags={"script", "style"})
    # nh3 metni HTML-escape eder; kelime sayımı için önemsizdir.
    return re.sub(r"\s+", " ", text).strip()
