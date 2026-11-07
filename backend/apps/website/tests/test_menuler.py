"""Menüler: PUT ağacı, href çözümü, public filtreleme ve site ucu."""
from unittest.mock import patch

import pytest

from apps.website.models import MenuOgesi

pytestmark = pytest.mark.django_db

MENU = "/api/website/admin/menuler/"


def _oge(etiket, link_tipi, sayfa_id=None, anchor="", url="", cta=False, aktif=True, cocuklar=None, **ek):
    return {
        "etiket": etiket, "link_tipi": link_tipi, "sayfa_id": sayfa_id, "bolum_anchor": anchor, "url": url,
        "yeni_sekme": False, "cta": cta, "aktif": aktif, "cocuklar": cocuklar or [], **ek,
    }


def test_menu_put_href_cozumu_ve_public_filtre(editor_client, site_istemci, sayfa_olustur):
    ana = sayfa_olustur(slug="anasayfa", yayinla=True)
    tek = sayfa_olustur(slug="teknoloji", yayinla=True)
    taslak = sayfa_olustur(slug="taslak-sayfa", yayinla=False)

    govde = [
        _oge("Çözüm", "bolum", ana.pk, "nasil-calisir", cocuklar=[
            _oge("SSS", "bolum", ana.pk, "#sss"),
            _oge("Taslak alt", "sayfa", taslak.pk),
            _oge("Pasif alt", "blog", aktif=False),
        ]),
        _oge("Teknoloji", "bolum", tek.pk, "kiosk"),
        _oge("Blog", "blog"),
        _oge("Taslak", "sayfa", taslak.pk, cocuklar=[_oge("Taslağın çocuğu", "blog")]),
        _oge("WhatsApp", "dis", url="https://wa.me/905550000000"),
        _oge("Ücretsiz Pilot", "bolum", ana.pk, "pilot", cta=True),
    ]
    yanit = editor_client.put(f"{MENU}header/", govde, format="json")
    assert yanit.status_code == 200, yanit.data
    admin_agac = yanit.data
    assert [o["etiket"] for o in admin_agac] == ["Çözüm", "Teknoloji", "Blog", "Taslak", "WhatsApp", "Ücretsiz Pilot"]
    assert set(admin_agac[0]) == {
        "id", "etiket", "link_tipi", "sayfa_id", "bolum_anchor", "url", "yeni_sekme", "cta", "aktif", "href", "cocuklar",
    }
    assert admin_agac[0]["href"] == "/#nasil-calisir"
    assert admin_agac[0]["cocuklar"][0]["bolum_anchor"] == "sss"  # baştaki # temizlenir
    assert admin_agac[1]["href"] == "/teknoloji#kiosk"
    assert admin_agac[3]["href"] == "/taslak-sayfa"  # admin yanıtı yayında olmayanı da gösterir

    site = site_istemci.get("/api/website/public/site/")
    assert site.status_code == 200 and site["Cache-Control"] == "public, max-age=60"
    header = site.data["menuler"]["header"]
    assert [o["etiket"] for o in header] == ["Çözüm", "Teknoloji", "Blog", "WhatsApp", "Ücretsiz Pilot"]
    assert set(header[0]) == {"id", "etiket", "href", "yeni_sekme", "cta", "cocuklar"}
    assert [c["etiket"] for c in header[0]["cocuklar"]] == ["SSS"]  # taslak sayfaya bağlı ve pasif alt öğe gizli
    assert header[0]["cocuklar"][0]["href"] == "/#sss"
    assert header[2]["href"] == "/blog"
    assert header[3]["href"] == "https://wa.me/905550000000"
    assert header[4]["cta"] is True
    assert site.data["menuler"]["footer"] == [] and site.data["menuler"]["footer_alt"] == []

    # Sayfa yayına alınınca öğe görünür.
    editor_client.post(f"/api/website/admin/sayfalar/{taslak.pk}/yayinla/")
    header = site_istemci.get("/api/website/public/site/").data["menuler"]["header"]
    assert "Taslak" in [o["etiket"] for o in header]


def test_menu_put_id_korur_ve_atomik_degistirir(editor_client, sayfa_olustur):
    ana = sayfa_olustur(slug="anasayfa", yayinla=True)
    ilk = editor_client.put(f"{MENU}footer/", [_oge("Ürün", "bolum", ana.pk, "urun", cocuklar=[_oge("Blog", "blog")])], format="json").data
    urun_id, blog_id = ilk[0]["id"], ilk[0]["cocuklar"][0]["id"]

    # Çocuk kök seviyeye taşınır, kök silinir.
    ikinci = editor_client.put(f"{MENU}footer/", [_oge("Blog", "blog", id=blog_id)], format="json").data
    assert ikinci[0]["id"] == blog_id and ikinci[0]["cocuklar"] == []
    assert not MenuOgesi.objects.filter(pk=urun_id).exists()
    assert MenuOgesi.objects.filter(menu__konum="footer").count() == 1


def test_menu_dogrulama_hatalari(editor_client, sayfa_olustur):
    ana = sayfa_olustur(slug="anasayfa")
    govde = [
        _oge("", "sayfa"),
        _oge("Kötü link", "dis", url="javascript:alert(1)"),
        _oge("Bölüm", "bolum", ana.pk, ""),
        _oge("Derin", "blog", cocuklar=[_oge("Alt", "blog", cocuklar=[_oge("Torun", "blog")])]),
        _oge("Yok", "sayfa", 999999),
        _oge("Tip", "bilinmeyen"),
    ]
    yanit = editor_client.put(f"{MENU}header/", govde, format="json")
    assert yanit.status_code == 400
    h = yanit.data
    assert h["0"] == {"etiket": ["Bu alan zorunludur."], "sayfa_id": ["Bu alan zorunludur."]}
    assert "url" in h["1"]
    assert h["2"] == {"bolum_anchor": ["Bu alan zorunludur."]}
    assert h["3"] == {"cocuklar": {"0": {"cocuklar": ["Menü en fazla 2 seviyeli olabilir."]}}}
    assert h["4"] == {"sayfa_id": ["Sayfa bulunamadı."]}
    assert h["5"] == {"link_tipi": ["Geçersiz bağlantı tipi."]}
    assert MenuOgesi.objects.count() == 0

    assert editor_client.put(f"{MENU}yan-menu/", [], format="json").status_code == 404
    assert editor_client.put(f"{MENU}header/", {"x": 1}, format="json").status_code == 400


def test_menu_put_site_tagini_revalidate_eder(editor_client, django_capture_on_commit_callbacks):
    with patch("apps.website.services.revalidate.revalidate_gonder") as gonder:
        with django_capture_on_commit_callbacks(execute=True):
            assert editor_client.put(f"{MENU}footer_alt/", [_oge("Blog", "blog")], format="json").status_code == 200
    gonder.assert_called_once_with(["site"])


def test_admin_menuler_get_ucu(editor_client, sayfa_olustur):
    ana = sayfa_olustur(slug="anasayfa")
    editor_client.put(f"{MENU}footer_alt/", [_oge("KVKK", "sayfa", ana.pk)], format="json")
    yanit = editor_client.get(MENU)
    assert set(yanit.data) == {"header", "footer", "footer_alt"}
    assert yanit.data["footer_alt"][0]["href"] == "/"
