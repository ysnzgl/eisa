"""Portal "Sitede ara" — /api/website/admin/arama/."""
import pytest

from apps.website.services.arama import normalize, parca_uret

from .conftest import ornek_hero

URL = "/api/website/admin/arama/"


def test_normalize_turkce_ve_uzunluk_korunur():
    metin = "SAĞLIK İçin IŞIK Çözüm"
    n = normalize(metin)
    assert len(n) == len(metin)
    assert n == "saglik icin isik cozum"


def test_parca_baglam_ve_adet():
    p = parca_uret("Eczacı her zaman eczacıdır; ECZACI kontrolü.", normalize("eczaci"))
    assert p["eslesen"] == "Eczacı" and p["onceki"] == "" and p["adet"] == 3


@pytest.mark.django_db
def test_yetkisiz_erisim(site_istemci, eczaci_api):
    assert site_istemci.get(URL, {"q": "test"}).status_code in (401, 403)
    assert eczaci_api.get(URL, {"q": "test"}).status_code == 403


@pytest.mark.django_db
def test_kisa_sorgu_bos_doner(editor_client):
    yanit = editor_client.get(URL, {"q": "a"})
    assert yanit.status_code == 200 and yanit.data["sonuclar"] == []


@pytest.mark.django_db
def test_blok_ic_ice_liste_alani_bulunur(editor_client, sayfa_olustur):
    sayfa = sayfa_olustur(
        slug="hizmet",
        baslik="Hizmetler",
        bloklar=[
            {"tip": "hero", "veri": ornek_hero()},
            {
                "tip": "ozellik_kartlari",
                "veri": {"baslik": "Neden biz", "sutun": "3", "arka_plan": "acik",
                         "kartlar": [{"ikon": "Brain", "baslik": "Hızlı", "metin": "Kısa süre"},
                                     {"ikon": "Pill", "baslik": "Güvenli", "metin": "Eczacı ONAYLI öneri"}]},
                "gorunur": False,
            },
        ],
    )
    yanit = editor_client.get(URL, {"q": "eczaci onayli"})
    assert yanit.status_code == 200
    s = yanit.data["sonuclar"]
    assert len(s) == 1
    r = s[0]
    assert r["grup"] == {"tur": "sayfa", "id": sayfa.pk, "baslik": "Hizmetler", "slug": "hizmet", "durum": sayfa.durum}
    assert r["blok"]["tip"] == "ozellik_kartlari" and r["blok"]["gizli"] is True
    assert r["hedef"]["alan"] == "kartlar.1.metin"
    assert r["konum"] == ["Özellik Kartları", "Kartlar", "2. öğe", "Metin"]
    assert r["parca"]["eslesen"] == "Eczacı ONAYLI"


@pytest.mark.django_db
def test_sayfa_meta_blog_menu_ayar_kapsami(editor_client, sayfa_olustur):
    from apps.website.models import BlogYazisi, Menu, MenuOgesi, SiteAyarlari

    sayfa = sayfa_olustur(slug="pilot", baslik="Pilot Zebra", bloklar=[{"tip": "hero", "veri": ornek_hero()}])
    BlogYazisi.objects.create(slug="y1", baslik="Yazı", icerik_html="<p>Bir <strong>zebra</strong> &amp; at</p>")
    menu = Menu.objects.create(konum="header")
    MenuOgesi.objects.create(menu=menu, etiket="Zebra Menü", link_tipi="dis", url="https://example.com", sira=0)
    SiteAyarlari.objects.create(pk=1, footer_aciklama="Zebra footer")

    yanit = editor_client.get(URL, {"q": "ZEBRA"})
    hedefler = {(r["hedef"]["ekran"], r["hedef"]["alan"]) for r in yanit.data["sonuclar"]}
    assert ("sayfa", "meta:baslik") in hedefler
    assert ("blog", "icerik_html") in hedefler
    assert ("menu", "etiket") in hedefler
    assert ("ayarlar", "footer_aciklama") in hedefler
    blog = next(r for r in yanit.data["sonuclar"] if r["hedef"]["ekran"] == "blog")
    assert "<" not in blog["parca"]["onceki"] + blog["parca"]["sonraki"]  # HTML ayıklanır
    assert yanit.data["toplam"] == len(yanit.data["sonuclar"])
    assert sayfa.pk == next(r for r in yanit.data["sonuclar"] if r["hedef"]["ekran"] == "sayfa")["hedef"]["sayfa_id"]


@pytest.mark.django_db
def test_sonuc_siniri(editor_client, sayfa_olustur, monkeypatch):
    from apps.website.services import arama

    monkeypatch.setattr(arama, "MAX_SONUC", 2)
    for i in range(3):
        sayfa_olustur(slug=f"s{i}", baslik=f"Ortak kelime {i}", bloklar=[{"tip": "hero", "veri": ornek_hero()}])
    yanit = editor_client.get(URL, {"q": "ortak kelime"})
    assert len(yanit.data["sonuclar"]) == 2 and yanit.data["toplam"] == 3 and yanit.data["kesildi"] is True

@pytest.mark.django_db
def test_sayi_kategori_ve_medya_kapsami(editor_client, sayfa_olustur, medya_olustur):
    from apps.website.models import BlogKategori

    sayfa_olustur(slug="kazanc", bloklar=[{
        "tip": "kazanc_hesaplayici",
        "veri": {"baslik": "Kazanç", "kademeler": [{"etkilesim_min": 1, "etkilesim_max": 10, "gunluk_satis": 1,
                                                    "aylik_satis": 25, "aylik_ciro": 18000, "aylik_kar": 6000}],
                 "varsayilan_etkilesim": 5, "slider_max": 10, "para_birimi": "TL", "uyari_notu": "Örnek", "tablo_goster": True},
    }])
    BlogKategori.objects.create(ad="Sağlık Okuryazarlığı", slug="saglik-okuryazarligi")
    medya_olustur(alt="Eczane vitrini fotoğrafı", dosya_adi="vitrin.png")

    # Sayı: sitede göründüğü biçim de ham biçim de bulunur
    for q in ("18.000", "18000"):
        s = editor_client.get(URL, {"q": q}).data["sonuclar"]
        assert [r["hedef"]["alan"] for r in s] == ["kademeler.0.aylik_ciro"], q
        assert s[0]["konum"][-1] == "Aylık ciro"

    s = editor_client.get(URL, {"q": "saglik okuryazarligi"}).data["sonuclar"]
    assert {r["hedef"]["ekran"] for r in s} == {"blog_kategori"}

    s = editor_client.get(URL, {"q": "VİTRİN"}).data["sonuclar"]
    assert {(r["hedef"]["ekran"], r["hedef"]["alan"]) for r in s} == {("medya", "alt"), ("medya", "dosya_adi")}