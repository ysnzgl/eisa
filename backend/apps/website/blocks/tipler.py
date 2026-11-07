"""
CONTRACT §8 — Blok kataloğu. Her tip için `veri` alan şeması burada tanımlanır.

Kısaltma (sözleşmedeki `?`): opsiyonel alan → zorunlu=False.
`[Buton]` listeleri `liste` + Buton alt alanları (etiket, href, stil) olarak tanımlanır;
böylece veri biçimi birebir `[{etiket, href, stil}]` olur.
"""
from __future__ import annotations

from typing import Callable

from .alanlar import Alan, buton_alanlari

# ── Kısa yardımcılar ────────────────────────────────────────────────────────


def metin(ad, etiket, zorunlu=False, max_uzunluk=200, yardim="", **kw) -> Alan:
    return Alan(ad, etiket, "metin", zorunlu=zorunlu, max_uzunluk=max_uzunluk, yardim=yardim, **kw)


def uzun_metin(ad, etiket, zorunlu=False, max_uzunluk=2000, yardim="", **kw) -> Alan:
    return Alan(ad, etiket, "uzun_metin", zorunlu=zorunlu, max_uzunluk=max_uzunluk, yardim=yardim, **kw)


def sayi(ad, etiket, min=None, max=None, varsayilan=None, yardim="") -> Alan:  # noqa: A002
    kw = {} if varsayilan is None else {"varsayilan": varsayilan}
    return Alan(ad, etiket, "sayi", zorunlu=True, min=min, max=max, yardim=yardim, **kw)


def evet_hayir(ad, etiket, varsayilan=False, yardim="") -> Alan:
    return Alan(ad, etiket, "bool", zorunlu=True, varsayilan=varsayilan, yardim=yardim)


def secim(ad, etiket, secenekler, varsayilan=None, yardim="") -> Alan:
    kw = {} if varsayilan is None else {"varsayilan": varsayilan}
    return Alan(
        ad, etiket, "secim", zorunlu=True, yardim=yardim,
        secenekler=[{"deger": d, "etiket": e} for d, e in secenekler], **kw,
    )


def ikon(ad="ikon", etiket="İkon") -> Alan:
    return Alan(ad, etiket, "ikon", zorunlu=True)


def medya(ad, etiket, zorunlu=False, yardim="") -> Alan:
    return Alan(ad, etiket, "medya", zorunlu=zorunlu, yardim=yardim)


def liste(ad, etiket, alanlar, min_adet=0, max_adet=None, yardim="") -> Alan:
    return Alan(ad, etiket, "liste", alanlar=alanlar, min_adet=min_adet, max_adet=max_adet, yardim=yardim)


def butonlar(min_adet, max_adet) -> Alan:
    return liste("butonlar", "Butonlar", buton_alanlari(), min_adet=min_adet, max_adet=max_adet)


def arka_plan() -> Alan:
    return secim("arka_plan", "Arka plan", [("acik", "Açık"), ("gri", "Gri"), ("koyu", "Koyu")], "acik")


def ust_baslik() -> Alan:
    return metin("ust_baslik", "Üst başlık", max_uzunluk=80, yardim="Başlığın üstündeki küçük etiket.")


def baslik(zorunlu=True, max_uzunluk=160) -> Alan:
    return metin("baslik", "Başlık", zorunlu=zorunlu, max_uzunluk=max_uzunluk)


def aciklama() -> Alan:
    return uzun_metin("aciklama", "Açıklama", max_uzunluk=1000)


# ── Blok tipi ───────────────────────────────────────────────────────────────


class BlokTipi:
    def __init__(
        self,
        tip: str,
        ad: str,
        aciklama: str,
        ikon: str,
        alanlar: list[Alan],
        ek_dogrulama: Callable[[dict, dict], None] | None = None,
    ) -> None:
        self.tip = tip
        self.ad = ad
        self.aciklama = aciklama
        self.ikon = ikon
        self.alanlar = alanlar
        self.ek_dogrulama = ek_dogrulama

    def sema(self) -> dict:
        return {
            "tip": self.tip,
            "ad": self.ad,
            "aciklama": self.aciklama,
            "ikon": self.ikon,
            "alanlar": [a.to_dict() for a in self.alanlar],
        }


def _vurgu_basliktami(veri: dict, hatalar: dict) -> None:
    vurgu = veri.get("vurgu") or ""
    if vurgu and "baslik" not in hatalar and vurgu not in (veri.get("baslik") or ""):
        hatalar["vurgu"] = ["Vurgu metni başlığın içinde birebir geçmelidir."]


def _kazanc_dogrula(veri: dict, hatalar: dict) -> None:
    if "kademeler" not in hatalar:
        kademe_hatalari = {}
        for i, k in enumerate(veri.get("kademeler") or []):
            if k.get("etkilesim_min", 0) > k.get("etkilesim_max", 0):
                kademe_hatalari[str(i)] = {
                    "etkilesim_max": ["Etkileşim üst sınırı alt sınırdan küçük olamaz."]
                }
        if kademe_hatalari:
            hatalar["kademeler"] = kademe_hatalari
    if (
        "varsayilan_etkilesim" not in hatalar
        and "slider_max" not in hatalar
        and veri.get("varsayilan_etkilesim", 0) > veri.get("slider_max", 0)
    ):
        hatalar["varsayilan_etkilesim"] = ["Varsayılan etkileşim kaydırıcı üst sınırını aşamaz."]


_SLUG_YARDIM = "Yalnızca küçük harf, rakam ve tire (ör. kvkk)."


def _kvkk_slug_dogrula(veri: dict, hatalar: dict) -> None:
    import re

    slug = veri.get("kvkk_sayfa_slug") or ""
    if "kvkk_sayfa_slug" not in hatalar and not re.match(r"^[a-z0-9-]+$", slug):
        hatalar["kvkk_sayfa_slug"] = [_SLUG_YARDIM]


def _kategori_slug_dogrula(veri: dict, hatalar: dict) -> None:
    import re

    slug = veri.get("kategori_slug") or ""
    if slug and "kategori_slug" not in hatalar and not re.match(r"^[a-z0-9-]+$", slug):
        hatalar["kategori_slug"] = [_SLUG_YARDIM]


VARSAYILAN_UYARI_NOTU = (
    "Bu değerler garanti değildir; örnek senaryo ve potansiyel etki olarak sunulmuştur. "
    "Gerçek sonuçlar eczanenin konumuna, hasta profiline ve ürün portföyüne göre değişebilir."
)
VARSAYILAN_BASARI_MESAJI = "Başvurunuz alındı. Ekibimiz en kısa sürede sizinle iletişime geçecek."


BLOK_TIPLERI_LISTESI: list[BlokTipi] = [
    BlokTipi(
        "hero", "Hero (Anasayfa)",
        "Koyu zeminli açılış bölümü: başlık, vurgu kartları, butonlar ve kiosk animasyonu.",
        "Sparkle",
        [
            metin("rozet", "Rozet", max_uzunluk=80),
            baslik(),
            metin("vurgu", "Vurgu", max_uzunluk=120, yardim="Başlık içinde kırmızı vurgulanacak alt metin (başlıkta birebir geçmeli)."),
            uzun_metin("alt_metin", "Alt metin", max_uzunluk=600),
            liste("vurgu_kartlari", "Vurgu kartları", [ikon(), metin("metin", "Metin", zorunlu=True, max_uzunluk=120)], 0, 6),
            butonlar(0, 3),
            evet_hayir("kiosk_animasyonu", "Kiosk animasyonu", varsayilan=True),
        ],
        _vurgu_basliktami,
    ),
    BlokTipi(
        "sayfa_basligi", "Sayfa Başlığı (iç sayfalar)",
        "İç sayfaların üst başlık alanı.",
        "Target",
        [
            metin("rozet", "Rozet", max_uzunluk=80),
            baslik(),
            metin("vurgu", "Vurgu", max_uzunluk=120, yardim="Başlık içinde kırmızı vurgulanacak alt metin (başlıkta birebir geçmeli)."),
            uzun_metin("alt_metin", "Alt metin", max_uzunluk=600),
            butonlar(0, 2),
        ],
        _vurgu_basliktami,
    ),
    BlokTipi(
        "ozellik_kartlari", "Özellik Kartları",
        "İkon, başlık ve metinden oluşan kart ızgarası.",
        "Lightbulb",
        [
            ust_baslik(),
            baslik(zorunlu=False),
            aciklama(),
            secim("sutun", "Sütun sayısı", [(2, "2"), (3, "3"), (4, "4")], 3),
            liste(
                "kartlar", "Kartlar",
                [ikon(), metin("baslik", "Başlık", zorunlu=True, max_uzunluk=100), uzun_metin("metin", "Metin", zorunlu=True, max_uzunluk=600)],
                1, 12,
            ),
            arka_plan(),
        ],
    ),
    BlokTipi(
        "vurgu_bandi", "Vurgu Bandı",
        "Slogan veya öne çıkan mesaj bandı.",
        "Lightning",
        [
            ikon(),
            baslik(),
            uzun_metin("metin", "Metin", max_uzunluk=1000),
            metin("vurgu_cumlesi", "Vurgu cümlesi", max_uzunluk=200),
            secim("stil", "Stil", [("kirmizi", "Kırmızı"), ("koyu", "Koyu"), ("acik", "Açık")], "acik"),
        ],
    ),
    BlokTipi(
        "scroll_hikaye", "Scroll Hikâye (Kiosk)",
        "Kaydırdıkça kiosk ekranının adım adım değiştiği sabitlenmiş anlatım.",
        "Devices",
        [
            ust_baslik(),
            baslik(),
            aciklama(),
            liste(
                "adimlar", "Adımlar",
                [
                    metin("baslik", "Başlık", zorunlu=True, max_uzunluk=100),
                    uzun_metin("metin", "Metin", zorunlu=True, max_uzunluk=600),
                    metin("ekran_baslik", "Ekran başlığı", zorunlu=True, max_uzunluk=60),
                    uzun_metin("ekran_metin", "Ekran metni", zorunlu=True, max_uzunluk=200),
                ],
                2, 6,
            ),
        ],
    ),
    BlokTipi(
        "surec_adimlari", "Süreç Adımları",
        "Numaralı adım / zaman çizelgesi.",
        "ArrowsClockwise",
        [
            ust_baslik(),
            baslik(),
            aciklama(),
            liste(
                "adimlar", "Adımlar",
                [metin("baslik", "Başlık", zorunlu=True, max_uzunluk=100), uzun_metin("metin", "Metin", zorunlu=True, max_uzunluk=600)],
                2, 8,
            ),
            arka_plan(),
        ],
    ),
    BlokTipi(
        "gorsel_metin", "Görsel + Metin",
        "Bir tarafta görsel (boşsa dekoratif illüstrasyon), diğer tarafta metin ve maddeler.",
        "Monitor",
        [
            ust_baslik(),
            baslik(),
            uzun_metin("metin", "Metin", zorunlu=True, max_uzunluk=3000),
            liste("maddeler", "Maddeler", [ikon(), metin("metin", "Metin", zorunlu=True, max_uzunluk=160)], 0, 8),
            medya("gorsel", "Görsel", yardim="Boş bırakılırsa site dekoratif kiosk/teknoloji illüstrasyonu çizer."),
            secim("gorsel_konumu", "Görsel konumu", [("sag", "Sağ"), ("sol", "Sol")], "sag"),
            butonlar(0, 2),
            arka_plan(),
        ],
    ),
    BlokTipi(
        "kazanc_hesaplayici", "Kazanç Hesaplayıcı",
        "Günlük etkileşime göre örnek satış/ciro potansiyeli gösteren kaydırıcı.",
        "ChartLineUp",
        [
            ust_baslik(),
            baslik(),
            aciklama(),
            liste(
                "kademeler", "Kademeler",
                [
                    sayi("etkilesim_min", "Etkileşim (alt)", min=0),
                    sayi("etkilesim_max", "Etkileşim (üst)", min=0),
                    sayi("gunluk_satis", "Günlük satış", min=0),
                    sayi("aylik_satis", "Aylık satış", min=0),
                    sayi("aylik_ciro", "Aylık ciro", min=0),
                    sayi("aylik_kar", "Aylık kâr", min=0),
                ],
                1, 10,
                yardim="Kaydırıcı değeri için koşulu sağlayan ilk kademe kullanılır.",
            ),
            sayi("varsayilan_etkilesim", "Varsayılan etkileşim", min=0, varsayilan=15),
            sayi("slider_max", "Kaydırıcı üst sınırı", min=1, varsayilan=50),
            metin("para_birimi", "Para birimi", zorunlu=True, max_uzunluk=10, varsayilan="TL"),
            uzun_metin("uyari_notu", "Uyarı notu", zorunlu=True, max_uzunluk=600, varsayilan=VARSAYILAN_UYARI_NOTU),
            evet_hayir("tablo_goster", "Tabloyu göster", varsayilan=True),
        ],
        _kazanc_dogrula,
    ),
    BlokTipi(
        "sayaclar", "Sayaçlar",
        "Animasyonlu sayı göstergeleri.",
        "TrendUp",
        [
            baslik(zorunlu=False),
            liste(
                "ogeler", "Öğeler",
                [
                    sayi("deger", "Değer"),
                    metin("onek", "Önek", max_uzunluk=10),
                    metin("sonek", "Sonek", max_uzunluk=20),
                    metin("etiket", "Etiket", zorunlu=True, max_uzunluk=80),
                ],
                1, 6,
            ),
            arka_plan(),
        ],
    ),
    BlokTipi(
        "logo_bandi", "Logo Bandı",
        "Sponsor / iş ortağı logoları.",
        "Handshake",
        [
            baslik(zorunlu=False),
            liste(
                "logolar", "Logolar",
                [
                    medya("gorsel", "Logo", zorunlu=True),
                    metin("ad", "Ad", zorunlu=True, max_uzunluk=100),
                    metin("url", "Bağlantı", max_uzunluk=500, link=True),
                ],
                0, 30,
            ),
            metin("bos_mesaj", "Boş mesajı", max_uzunluk=200, yardim="Logo yokken gösterilecek metin."),
        ],
    ),
    BlokTipi(
        "sss", "SSS",
        "Sık sorulan sorular (akordeon).",
        "ChatCircleText",
        [
            ust_baslik(),
            baslik(),
            aciklama(),
            liste(
                "sorular", "Sorular",
                [metin("soru", "Soru", zorunlu=True, max_uzunluk=300), uzun_metin("cevap", "Cevap", zorunlu=True, max_uzunluk=2000)],
                1, 30,
            ),
            arka_plan(),
        ],
    ),
    BlokTipi(
        "cta_banner", "CTA Bandı",
        "Güçlü çağrı bandı.",
        "Rocket",
        [
            metin("rozet", "Rozet", max_uzunluk=80),
            baslik(),
            uzun_metin("metin", "Metin", max_uzunluk=600),
            butonlar(1, 2),
            secim("stil", "Stil", [("koyu", "Koyu"), ("kirmizi", "Kırmızı")], "koyu"),
        ],
    ),
    BlokTipi(
        "basvuru_formu", "Başvuru Formu",
        "Pilot / sponsor / genel başvuru formu (KVKK onaylı).",
        "Envelope",
        [
            ust_baslik(),
            baslik(),
            aciklama(),
            secim("form_tipi", "Form tipi", [("pilot", "Pilot"), ("sponsor", "Sponsor"), ("genel", "Genel")], "pilot"),
            liste(
                "maddeler", "Maddeler",
                [ikon(), metin("baslik", "Başlık", zorunlu=True, max_uzunluk=100), uzun_metin("metin", "Metin", zorunlu=True, max_uzunluk=300)],
                0, 6,
            ),
            uzun_metin("basari_mesaji", "Başarı mesajı", zorunlu=True, max_uzunluk=400, varsayilan=VARSAYILAN_BASARI_MESAJI),
            metin("kvkk_sayfa_slug", "KVKK sayfası", zorunlu=True, max_uzunluk=100, varsayilan="kvkk", yardim=_SLUG_YARDIM),
            evet_hayir("iletisim_bilgisi_goster", "İletişim bilgilerini göster", varsayilan=False),
        ],
        _kvkk_slug_dogrula,
    ),
    BlokTipi(
        "blog_son_yazilar", "Son Blog Yazıları",
        "En son yayınlanan blog yazılarının kartları.",
        "Megaphone",
        [
            baslik(zorunlu=False),
            aciklama(),
            sayi("adet", "Adet", min=1, max=6, varsayilan=3),
            metin("kategori_slug", "Kategori", max_uzunluk=100, yardim="Boşsa tüm kategoriler."),
        ],
        _kategori_slug_dogrula,
    ),
    BlokTipi(
        "ekip", "Ekip",
        "Kişi kartları.",
        "Users",
        [
            ust_baslik(),
            baslik(),
            aciklama(),
            liste(
                "kisiler", "Kişiler",
                [
                    metin("ad_soyad", "Ad soyad", zorunlu=True, max_uzunluk=100),
                    metin("unvan", "Unvan", zorunlu=True, max_uzunluk=100),
                    uzun_metin("biyografi", "Biyografi", max_uzunluk=1000),
                    medya("foto", "Fotoğraf"),
                    metin("linkedin", "LinkedIn", max_uzunluk=300, link=True),
                ],
                1, 24,
            ),
        ],
    ),
    BlokTipi(
        "zengin_metin", "Zengin Metin",
        "Serbest metin (KVKK, çerez politikası vb.).",
        "Receipt",
        [
            baslik(zorunlu=False),
            Alan("icerik_html", "İçerik", "zengin_metin", zorunlu=True),
            secim("genislik", "Genişlik", [("dar", "Dar"), ("genis", "Geniş")], "dar"),
            metin("son_guncelleme", "Son güncelleme", max_uzunluk=60, yardim="Ör. 7 Kasım 2026"),
        ],
    ),
]
