"""Blog: admin CRUD, sanitize, yayın tarihi filtresi, sayfalama, kategori ve revalidate."""
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.core.uow import save_new
from apps.website.models import BlogKategori, BlogYazisi

pytestmark = pytest.mark.django_db

ADMIN = "/api/website/admin/blog/"
PUBLIC = "/api/website/public/blog/"


@pytest.fixture
def kategori(db):
    return save_new(BlogKategori(ad="Sağlık Okuryazarlığı", slug="saglik-okuryazarligi"))


def _yazi(slug, durum="yayinda", gun=-1, kategori=None, **ek):
    return save_new(
        BlogYazisi(
            slug=slug, baslik=slug.title(), durum=durum, kategori=kategori,
            yayin_tarihi=timezone.now() + timedelta(days=gun) if gun is not None else None,
            icerik_html="<p>içerik</p>", **ek,
        )
    )


def test_public_yalnizca_yayinda_ve_tarihi_gelmis(site_istemci, kategori):
    _yazi("gecmis", gun=-2, kategori=kategori)
    _yazi("yeni", gun=-1)
    _yazi("gelecek", gun=+3)
    _yazi("taslak", durum="taslak")
    _yazi("arsiv", durum="arsiv")

    yanit = site_istemci.get(PUBLIC)
    assert yanit.status_code == 200 and yanit["Cache-Control"] == "public, max-age=60"
    assert [y["slug"] for y in yanit.data["sonuclar"]] == ["yeni", "gecmis"]  # -yayin_tarihi
    assert yanit.data["toplam"] == 2 and yanit.data["sayfa"] == 1 and yanit.data["sayfa_sayisi"] == 1
    assert yanit.data["kategoriler"] == [{"ad": "Sağlık Okuryazarlığı", "slug": "saglik-okuryazarligi"}]
    ozet = yanit.data["sonuclar"][1]
    assert set(ozet) == {"slug", "baslik", "ozet", "kapak", "kategori", "etiketler", "yazar_adi", "yayin_tarihi", "okuma_suresi"}
    assert ozet["kategori"] == {"ad": "Sağlık Okuryazarlığı", "slug": "saglik-okuryazarligi"}

    for slug in ("gelecek", "taslak", "arsiv"):
        assert site_istemci.get(f"{PUBLIC}{slug}/").status_code == 404

    filtreli = site_istemci.get(PUBLIC, {"kategori": "saglik-okuryazarligi"}).data
    assert [y["slug"] for y in filtreli["sonuclar"]] == ["gecmis"]


def test_public_sayfalama_ve_boyut_siniri(site_istemci):
    for i in range(30):
        _yazi(f"yazi-{i:02d}", gun=-(i + 1))
    yanit = site_istemci.get(PUBLIC, {"sayfa": 2, "boyut": 9}).data
    assert yanit["toplam"] == 30 and yanit["sayfa"] == 2 and yanit["sayfa_sayisi"] == 4
    assert [y["slug"] for y in yanit["sonuclar"]][0] == "yazi-09"
    buyuk = site_istemci.get(PUBLIC, {"boyut": 500}).data
    assert len(buyuk["sonuclar"]) == 24
    gecersiz = site_istemci.get(PUBLIC, {"sayfa": "abc", "boyut": "-3"}).data
    assert gecersiz["sayfa"] == 1 and len(gecersiz["sonuclar"]) == 9


def test_public_detay_ve_ilgili(site_istemci, kategori):
    ana = _yazi("ana", gun=-1, kategori=kategori, seo_baslik="SEO", ozet="Özet")
    for i in range(4):
        _yazi(f"ilgili-{i}", gun=-(i + 2), kategori=kategori)
    _yazi("baska-kategori", gun=-1)
    yanit = site_istemci.get(f"{PUBLIC}ana/")
    assert yanit.status_code == 200
    d = yanit.data
    assert d["icerik_html"] == "<p>içerik</p>"
    assert d["seo"] == {"baslik": "SEO", "aciklama": "Özet", "og_gorsel": None}
    assert len(d["ilgili"]) == 3 and all(i["slug"].startswith("ilgili-") for i in d["ilgili"])
    assert ana.slug not in [i["slug"] for i in d["ilgili"]]


def test_admin_yazi_olustur_sanitize_okuma_suresi_ve_yayin_tarihi(editor_client, kategori, medya_olustur):
    medya = medya_olustur()
    govde = {
        "baslik": "Dürtme Yaklaşımı Nedir?",
        "ozet": "Kısa özet",
        "kapak": {"id": medya.pk, "yol": "https://evil.com/x.png"},
        "icerik_html": "<p>" + "kelime " * 450 + '</p><script>alert(1)</script><a href="javascript:x">k</a>',
        "kategori_id": kategori.pk,
        "etiketler": ["nudge", " nudge ", "sağlık"],
        "yazar_adi": "e-isa Ekibi",
        "durum": "yayinda",
    }
    yanit = editor_client.post(f"{ADMIN}yazilar/", govde, format="json")
    assert yanit.status_code == 201, yanit.data
    d = yanit.data
    assert d["slug"] == "durtme-yaklasimi-nedir"
    assert "<script" not in d["icerik_html"] and "javascript" not in d["icerik_html"]
    assert d["okuma_suresi"] == 3
    assert d["yayin_tarihi"] is not None
    assert d["kapak"]["yol"] == f"/api/media/{medya.object_key}"
    assert d["etiketler"] == ["nudge", "sağlık"]
    assert set(d) == {
        "id", "slug", "baslik", "ozet", "kapak", "icerik_html", "kategori_id", "etiketler", "yazar_adi",
        "durum", "yayin_tarihi", "seo_baslik", "seo_aciklama", "okuma_suresi", "surum",
    }

    liste = editor_client.get(f"{ADMIN}yazilar/").data
    assert liste[0]["kategori"] == {"id": kategori.pk, "ad": kategori.ad}
    assert set(liste[0]) == {"id", "slug", "baslik", "durum", "kategori", "yayin_tarihi", "guncellenme_tarihi"}

    # Çakışan slug ve geçersiz slug
    assert editor_client.post(f"{ADMIN}yazilar/", {**govde, "kapak": None}, format="json").status_code == 400
    assert editor_client.post(f"{ADMIN}yazilar/", {"baslik": "X", "slug": "Kötü Slug"}, format="json").status_code == 400


def test_admin_yazi_patch_surum_ve_revalidate(editor_client, django_capture_on_commit_callbacks):
    yazi = _yazi("eski-slug", durum="taslak", gun=None)
    with patch("apps.website.services.revalidate.revalidate_gonder") as gonder:
        with django_capture_on_commit_callbacks(execute=True):
            yanit = editor_client.patch(
                f"{ADMIN}yazilar/{yazi.pk}/", {"slug": "yeni-slug", "surum": yazi.surum}, format="json"
            )
        assert yanit.status_code == 200
        gonder.assert_called_once_with(["blog", "blog:yeni-slug", "blog:eski-slug"])

        gonder.reset_mock()
        with django_capture_on_commit_callbacks(execute=True):
            yanit = editor_client.patch(f"{ADMIN}yazilar/{yazi.pk}/", {"baslik": "X", "surum": yazi.surum}, format="json")
        assert yanit.status_code == 409
        gonder.assert_not_called()

        with django_capture_on_commit_callbacks(execute=True):
            assert editor_client.delete(f"{ADMIN}yazilar/{yazi.pk}/").status_code == 204
        gonder.assert_called_once_with(["blog", "blog:yeni-slug"])


def test_kategori_crud(editor_client):
    yanit = editor_client.post(f"{ADMIN}kategoriler/", {"ad": "Eczane Yönetimi", "sira": 1}, format="json")
    assert yanit.status_code == 201 and yanit.data == {"id": yanit.data["id"], "ad": "Eczane Yönetimi", "slug": "eczane-yonetimi", "sira": 1}
    kid = yanit.data["id"]
    yazi = _yazi("bagli", kategori=BlogKategori.objects.get(pk=kid))
    assert editor_client.patch(f"{ADMIN}kategoriler/{kid}/", {"ad": "Yönetim"}, format="json").data["ad"] == "Yönetim"
    assert editor_client.post(f"{ADMIN}kategoriler/", {"ad": "Başka", "slug": "eczane-yonetimi"}, format="json").status_code == 400
    assert editor_client.delete(f"{ADMIN}kategoriler/{kid}/").status_code == 204
    yazi.refresh_from_db()
    assert yazi.kategori_id is None
    assert editor_client.get(f"{ADMIN}kategoriler/").data == []


def test_blog_onizleme_url(editor_client):
    yazi = _yazi("taslak-yazi", durum="taslak", gun=None)
    yanit = editor_client.post(f"{ADMIN}yazilar/{yazi.pk}/onizleme/")
    assert "tur=blog&slug=taslak-yazi&token=" in yanit.data["url"]
