"""website_seed komutu: CONTRACT §9 içeriği, idempotentlik, --force ve blok geçerliliği."""
import pytest
from django.core.management import call_command

from apps.website.blocks import bloklari_dogrula
from apps.website.models import BlogKategori, BlogYazisi, Blok, Menu, MenuOgesi, Sayfa, SayfaRevizyon, SiteAyarlari

pytestmark = pytest.mark.django_db

SLUGLAR = ["anasayfa", "teknoloji", "sponsorlar", "hakkimizda", "iletisim", "kvkk", "cerez-politikasi"]


def _sayilar():
    return {
        m.__name__: m.objects.count()
        for m in (Sayfa, Blok, SayfaRevizyon, Menu, MenuOgesi, BlogKategori, BlogYazisi, SiteAyarlari)
    }


def test_seed_icerik_ve_idempotent(site_istemci):
    call_command("website_seed")
    ilk = _sayilar()
    assert sorted(Sayfa.objects.values_list("slug", flat=True)) == sorted(SLUGLAR)
    assert all(s.durum == "yayinda" and s.aktif_revizyon_id for s in Sayfa.objects.all())
    assert ilk["BlogKategori"] == 3 and ilk["BlogYazisi"] == 3 and ilk["SiteAyarlari"] == 1

    call_command("website_seed")
    assert _sayilar() == ilk  # ikinci çalıştırma hiçbir şey değiştirmez

    # Anasayfa blok sırası ve anchor'ları (CONTRACT §9)
    ana = site_istemci.get("/api/website/public/sayfalar/anasayfa/").data
    assert [(b["tip"], b["anchor_id"]) for b in ana["bloklar"]] == [
        ("hero", ""), ("ozellik_kartlari", "nasil-calisir"), ("vurgu_bandi", ""),
        ("ozellik_kartlari", "eczaci-kontrolu"), ("scroll_hikaye", "yolculuk"), ("kazanc_hesaplayici", "kazanc"),
        ("ozellik_kartlari", ""), ("sss", "sss"), ("blog_son_yazilar", ""), ("basvuru_formu", "pilot"),
    ]
    hero = ana["bloklar"][0]["veri"]
    assert hero["butonlar"] == [
        {"etiket": "Pilot Süreci İncele", "href": "/#pilot", "stil": "birincil"},
        {"etiket": "Nasıl Çalışır?", "href": "/#nasil-calisir", "stil": "ikincil"},
    ]
    kazanc = ana["bloklar"][5]["veri"]
    assert [(k["etkilesim_min"], k["etkilesim_max"], k["aylik_ciro"], k["aylik_kar"]) for k in kazanc["kademeler"]] == [
        (1, 10, 18000, 6000), (10, 20, 56000, 18000), (20, 30, 110000, 36000), (30, 40, 185000, 62000), (40, 50, 280000, 94000),
    ]
    assert "garanti değildir" in kazanc["uyari_notu"]
    assert len(ana["bloklar"][7]["veri"]["sorular"]) == 5

    hakkimizda = site_istemci.get("/api/website/public/sayfalar/hakkimizda/").data
    ekip = next(b for b in hakkimizda["bloklar"] if b["tip"] == "ekip")["veri"]
    assert ekip["kisiler"][0]["ad_soyad"] == "Yasin ÖZGÜL" and ekip["kisiler"][0]["unvan"] == "Yazılım Mimarı"
    assert ekip["kisiler"][0]["foto"] is None

    kvkk = site_istemci.get("/api/website/public/sayfalar/kvkk/").data
    metin = kvkk["bloklar"][1]["veri"]["icerik_html"]
    assert "Eisa Bilişim Teknolojileri A.Ş." in metin and "11. maddesi" in metin and "iletisim@eisa.com.tr" in metin

    site = site_istemci.get("/api/website/public/site/").data
    assert site["ayarlar"]["eposta"] == "iletisim@eisa.com.tr"
    assert site["ayarlar"]["firma_unvani"] == "Eisa Bilişim Teknolojileri A.Ş."
    assert [s["platform"] for s in site["ayarlar"]["sosyal_linkler"]] == ["linkedin", "instagram"]
    header = site["menuler"]["header"]
    assert [o["etiket"] for o in header] == ["Çözüm", "Teknoloji", "Sponsorlar", "Blog", "Kurumsal", "1 Ay Ücretsiz Pilot"]
    assert [c["href"] for c in header[0]["cocuklar"]] == ["/#nasil-calisir", "/#eczaci-kontrolu", "/#yolculuk", "/#kazanc", "/#sss"]
    assert header[5] ["href"] == "/#pilot" and header[5]["cta"] is True
    assert [c["href"] for c in header[4]["cocuklar"]] == ["/hakkimizda", "/iletisim"]
    assert [o["etiket"] for o in site["menuler"]["footer"]] == ["Ürün", "Kurumsal"]
    assert [o["href"] for o in site["menuler"]["footer_alt"]] == ["/kvkk", "/cerez-politikasi"]

    blog = site_istemci.get("/api/website/public/blog/").data
    assert blog["toplam"] == 3 and len(blog["kategoriler"]) == 3


def test_seed_bloklari_registry_dogrulamasindan_gecer():
    call_command("website_seed")
    for sayfa in Sayfa.objects.prefetch_related("bloklar"):
        girdi = [{"tip": b.tip, "veri": b.veri, "gorunur": b.gorunur, "anchor_id": b.anchor_id} for b in sayfa.bloklar.all()]
        temiz, hatalar = bloklari_dogrula(girdi)
        assert hatalar == {}, (sayfa.slug, hatalar)
        # Kaydedilen veri zaten normalize: yeniden doğrulama aynı sonucu verir.
        assert [t["veri"] for t in temiz] == [g["veri"] for g in girdi]


def test_seed_mevcut_icerigi_yalnizca_force_ile_ezer():
    call_command("website_seed")
    ana = Sayfa.objects.get(slug="anasayfa")
    ana.baslik = "Elle değiştirildi"
    ana.save(update_fields=["baslik"])
    rev_sayisi = SayfaRevizyon.objects.count()

    call_command("website_seed")
    assert Sayfa.objects.get(slug="anasayfa").baslik == "Elle değiştirildi"

    call_command("website_seed", "--force")
    ana = Sayfa.objects.get(slug="anasayfa")
    assert ana.baslik == "Anasayfa"
    assert SayfaRevizyon.objects.count() == rev_sayisi + 7
    assert Sayfa.objects.count() == 7 and BlogYazisi.objects.count() == 3
    assert MenuOgesi.objects.filter(menu__konum="header", ust__isnull=True).count() == 6
