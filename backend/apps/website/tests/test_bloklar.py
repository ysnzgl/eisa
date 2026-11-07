"""Blok şema registry'si: doğrulama, normalizasyon, sanitize, href ve MediaRef."""
import pytest

from apps.website.blocks import BLOK_TIPLERI, IKONLAR, blok_tipleri_semasi, blok_verisi_dogrula, bloklari_dogrula
from apps.website.guvenlik import href_gecerli_mi, html_temizle

from .conftest import ornek_hero

pytestmark = pytest.mark.django_db

SOZLESME_TIPLERI = {
    "hero", "sayfa_basligi", "ozellik_kartlari", "vurgu_bandi", "scroll_hikaye", "surec_adimlari",
    "gorsel_metin", "kazanc_hesaplayici", "sayaclar", "logo_bandi", "sss", "cta_banner",
    "basvuru_formu", "blog_son_yazilar", "ekip", "zengin_metin",
}


def test_registry_sozlesmedeki_16_tipi_icerir():
    assert set(BLOK_TIPLERI) == SOZLESME_TIPLERI
    assert len(IKONLAR) == 48


def test_blok_tipleri_endpoint_semasi(editor_client):
    yanit = editor_client.get("/api/website/admin/blok-tipleri/")
    assert yanit.status_code == 200
    assert {t["tip"] for t in yanit.data} == SOZLESME_TIPLERI
    hero = next(t for t in yanit.data if t["tip"] == "hero")
    assert set(hero) == {"tip", "ad", "aciklama", "ikon", "alanlar"}
    alanlar = {a["ad"]: a for a in hero["alanlar"]}
    # Opsiyonel anahtarlar yalnızca ilgili tur için gelir.
    assert alanlar["baslik"]["tur"] == "metin" and alanlar["baslik"]["zorunlu"] is True
    assert "max_uzunluk" in alanlar["baslik"] and "secenekler" not in alanlar["baslik"]
    assert alanlar["kiosk_animasyonu"] == {
        "ad": "kiosk_animasyonu", "etiket": "Kiosk animasyonu", "tur": "bool",
        "zorunlu": True, "varsayilan": True, "yardim": "",
    }
    butonlar = alanlar["butonlar"]
    assert butonlar["tur"] == "liste" and butonlar["min_adet"] == 0 and butonlar["max_adet"] == 3
    assert [a["ad"] for a in butonlar["alanlar"]] == ["etiket", "href", "stil"]
    kart_ikon = alanlar["vurgu_kartlari"]["alanlar"][0]
    assert kart_ikon["tur"] == "ikon" and len(kart_ikon["secenekler"]) == 48
    kazanc = next(t for t in yanit.data if t["tip"] == "kazanc_hesaplayici")
    kademe = next(a for a in kazanc["alanlar"] if a["ad"] == "kademeler")
    assert kademe["alanlar"][0]["tur"] == "sayi" and "min" in kademe["alanlar"][0]


def test_gecerli_veri_normalize_edilir_bilinmeyenler_atilir_varsayilanlar_dolar():
    temiz, hatalar = blok_verisi_dogrula("hero", {**ornek_hero(), "kotu_anahtar": "x", "rozet": None})
    assert hatalar == {}
    assert "kotu_anahtar" not in temiz
    assert temiz["rozet"] == "" and temiz["kiosk_animasyonu"] is True
    assert temiz["vurgu_kartlari"] == []
    assert temiz["butonlar"] == [{"etiket": "Pilot", "href": "/#pilot", "stil": "birincil"}]

    temiz, hatalar = blok_verisi_dogrula("ozellik_kartlari", {"kartlar": [{"baslik": "A", "metin": "B", "fazla": 1}], "sutun": "4"})
    assert hatalar == {}
    assert temiz["sutun"] == 4 and temiz["arka_plan"] == "acik"
    assert temiz["kartlar"] == [{"ikon": "Sparkle", "baslik": "A", "metin": "B"}]


def test_gecersiz_veri_indeksli_hatalar():
    _, hatalar = blok_verisi_dogrula(
        "ozellik_kartlari",
        {"kartlar": [{"baslik": "Tamam", "metin": "x"}, {"baslik": "", "metin": "y", "ikon": "Yok"}], "sutun": 5, "arka_plan": "mor"},
    )
    assert hatalar["kartlar"] == {"1": {"baslik": ["Bu alan zorunludur."], "ikon": ["Geçersiz ikon."]}}
    assert hatalar["sutun"] == ["Geçersiz seçim."]
    assert hatalar["arka_plan"] == ["Geçersiz seçim."]

    _, hatalar = blok_verisi_dogrula("hero", {"baslik": "x" * 161})
    assert hatalar["baslik"] == ["En fazla 160 karakter olabilir."]

    _, hatalar = blok_verisi_dogrula("cta_banner", {"baslik": "CTA", "butonlar": []})
    assert hatalar["butonlar"] == ["En az 1 öğe olmalıdır."]

    _, hatalar = blok_verisi_dogrula("hero", {"baslik": "Başlık", "vurgu_kartlari": [{"metin": "a"}] * 7})
    assert hatalar["vurgu_kartlari"] == ["En fazla 6 öğe olabilir."]

    _, hatalar = blok_verisi_dogrula("blog_son_yazilar", {"adet": 9})
    assert hatalar["adet"] == ["En fazla 6 olabilir."]

    _, hatalar = blok_verisi_dogrula("hero", {"baslik": "Başlık", "vurgu": "yok"})
    assert "vurgu" in hatalar

    _, hatalar = blok_verisi_dogrula("bilinmeyen", {})
    assert hatalar == {"tip": ["Bilinmeyen blok tipi."]}


def test_kazanc_kademe_mantik_kontrolu():
    _, hatalar = blok_verisi_dogrula(
        "kazanc_hesaplayici",
        {
            "baslik": "K",
            "kademeler": [{"etkilesim_min": 20, "etkilesim_max": 10, "gunluk_satis": 1, "aylik_satis": 1, "aylik_ciro": 1, "aylik_kar": 1}],
            "varsayilan_etkilesim": 80,
            "slider_max": 50,
        },
    )
    assert hatalar["kademeler"] == {"0": {"etkilesim_max": ["Etkileşim üst sınırı alt sınırdan küçük olamaz."]}}
    assert "varsayilan_etkilesim" in hatalar

    temiz, hatalar = blok_verisi_dogrula(
        "kazanc_hesaplayici",
        {"baslik": "K", "kademeler": [{"etkilesim_min": "1", "etkilesim_max": 10.0, "gunluk_satis": 1, "aylik_satis": 25, "aylik_ciro": 18000, "aylik_kar": 6000}]},
    )
    assert hatalar == {}
    assert temiz["kademeler"][0]["etkilesim_min"] == 1 and isinstance(temiz["kademeler"][0]["etkilesim_max"], int)
    assert temiz["para_birimi"] == "TL" and "garanti değildir" in temiz["uyari_notu"]


@pytest.mark.parametrize(
    "href,gecerli",
    [
        ("/", True), ("/iletisim", True), ("/#pilot", True), ("#pilot", True),
        ("https://wa.me/905550000000", True), ("https://eisa.com.tr/blog", True),
        ("mailto:iletisim@eisa.com.tr", True), ("tel:+905550000000", True), ("tel:+90 555", False),
        ("javascript:alert(1)", False), ("JaVaScRiPt:alert(1)", False), ("http://eisa.com.tr", False),
        ("//evil.com", False), ("/\\evil.com", False), ("data:text/html,x", False), ("", False),
        ("https://", False), (" /bosluklu", False), ("vbscript:x", False), ("#", False),
    ],
)
def test_href_sema_kontrolu(href, gecerli):
    assert href_gecerli_mi(href) is gecerli


def test_buton_href_reddedilir():
    _, hatalar = blok_verisi_dogrula(
        "hero", {"baslik": "B", "butonlar": [{"etiket": "Kötü", "href": "javascript:alert(1)", "stil": "birincil"}]}
    )
    assert "href" in hatalar["butonlar"]["0"]
    _, hatalar = blok_verisi_dogrula("hero", {"baslik": "B", "butonlar": [{"etiket": "X", "href": "/a", "stil": "neon"}]})
    assert hatalar["butonlar"]["0"] == {"stil": ["Geçersiz seçim."]}


def test_zengin_metin_sanitize():
    kirli = (
        '<h2 onclick="x()">Başlık</h2><script>alert(1)</script><p style="color:red">Metin '
        '<a href="javascript:alert(1)">kötü</a> <a href="https://eisa.com.tr" target="_top">iyi</a></p>'
        '<img src="https://evil.com/x.png" onerror="alert(1)"><img src="/api/media/website/2026/11/a.webp" alt="A">'
        '<img src="https://api.eisa.com.tr/api/media/website/2026/11/b.webp"><iframe src="https://x"></iframe><h1>büyük</h1>'
    )
    temiz = html_temizle(kirli)
    assert "<script" not in temiz and "alert" not in temiz and "onclick" not in temiz and "onerror" not in temiz
    assert "style=" not in temiz and "<iframe" not in temiz and "<h1" not in temiz
    assert 'href="https://eisa.com.tr"' in temiz and 'rel="noopener noreferrer"' in temiz
    assert 'target="_top"' not in temiz
    assert "evil.com" not in temiz
    assert '<img src="/api/media/website/2026/11/a.webp" alt="A">' in temiz
    # Tam URL ile gelen kendi medyamız göreli yola indirgenir.
    assert '<img src="/api/media/website/2026/11/b.webp">' in temiz

    temiz_veri, hatalar = blok_verisi_dogrula("zengin_metin", {"icerik_html": kirli})
    assert hatalar == {} and temiz_veri["icerik_html"] == temiz
    _, hatalar = blok_verisi_dogrula("zengin_metin", {"icerik_html": "<script>x</script>"})
    assert hatalar["icerik_html"] == ["Bu alan zorunludur."]


def test_mediaref_dogrulanir_ve_dbden_tazelenir(medya_olustur):
    medya = medya_olustur(alt="Gerçek alt")
    sahte = {"id": medya.pk, "yol": "https://evil.com/x.png", "alt": "sahte", "genislik": 1, "yukseklik": 1, "mime": "text/html"}
    temiz, hatalar = blok_verisi_dogrula("gorsel_metin", {"baslik": "G", "metin": "M", "gorsel": sahte})
    assert hatalar == {}
    assert temiz["gorsel"] == {
        "id": medya.pk, "yol": f"/api/media/{medya.object_key}", "alt": "Gerçek alt",
        "genislik": 10, "yukseklik": 5, "mime": "image/png",
    }
    _, hatalar = blok_verisi_dogrula("gorsel_metin", {"baslik": "G", "metin": "M", "gorsel": {"id": 999999}})
    assert hatalar["gorsel"] == ["Medya bulunamadı."]
    _, hatalar = blok_verisi_dogrula("gorsel_metin", {"baslik": "G", "metin": "M", "gorsel": {"id": "abc"}})
    assert hatalar["gorsel"] == ["Geçersiz medya referansı."]
    # Logo bandında görsel zorunludur.
    _, hatalar = blok_verisi_dogrula("logo_bandi", {"logolar": [{"ad": "Marka", "gorsel": None}]})
    assert hatalar["logolar"] == {"0": {"gorsel": ["Bu alan zorunludur."]}}


def test_blok_listesi_anchor_ve_indeksli_hata():
    _, hatalar = bloklari_dogrula(
        [
            {"tip": "hero", "veri": ornek_hero(), "anchor_id": "ust"},
            {"tip": "sss", "veri": {"baslik": "S", "sorular": [{"soru": "a", "cevap": "b"}]}, "anchor_id": "ust"},
            {"tip": "sayfa_basligi", "veri": {}, "anchor_id": "Gecersiz Anchor"},
        ]
    )
    assert hatalar["1"] == {"anchor_id": ["Bu bölüm kimliği sayfada zaten kullanılıyor."]}
    assert hatalar["2"]["baslik"] == ["Bu alan zorunludur."]
    assert "anchor_id" in hatalar["2"]


def test_tum_tiplerin_varsayilan_semasi_tutarli():
    for sema in blok_tipleri_semasi():
        for alan in sema["alanlar"]:
            assert {"ad", "etiket", "tur", "zorunlu", "varsayilan", "yardim"} <= set(alan)
            if alan["tur"] == "secim":
                assert alan["varsayilan"] in [s["deger"] for s in alan["secenekler"]]
