"""Site ayarları (admin + public) ve revalidation servisi (fan-out, hata toleransı)."""
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from apps.website.services import revalidate as rv

pytestmark = pytest.mark.django_db


def test_ayarlar_get_patch_ve_public(editor_client, site_istemci, medya_olustur, django_capture_on_commit_callbacks):
    yanit = editor_client.get("/api/website/admin/ayarlar/")
    assert yanit.status_code == 200
    assert set(yanit.data) == {
        "site_adi", "seo_baslik_sablonu", "seo_aciklama", "og_gorsel", "eposta", "telefon", "whatsapp",
        "adres", "firma_unvani", "footer_aciklama", "sosyal_linkler",
    }
    medya = medya_olustur()
    with patch("apps.website.services.revalidate.revalidate_gonder") as gonder:
        with django_capture_on_commit_callbacks(execute=True):
            yanit = editor_client.patch(
                "/api/website/admin/ayarlar/",
                {
                    "eposta": "iletisim@eisa.com.tr",
                    "og_gorsel": {"id": medya.pk},
                    "sosyal_linkler": [{"platform": "linkedin", "url": "https://www.linkedin.com/company/e-isa"}],
                },
                format="json",
            )
        assert yanit.status_code == 200, yanit.data
        gonder.assert_called_once_with(["site"])
    assert yanit.data["og_gorsel"]["yol"] == f"/api/media/{medya.object_key}"

    site = site_istemci.get("/api/website/public/site/").data
    assert site["ayarlar"]["eposta"] == "iletisim@eisa.com.tr"
    assert site["ayarlar"]["sosyal_linkler"][0]["platform"] == "linkedin"

    hatali = editor_client.patch(
        "/api/website/admin/ayarlar/",
        {"seo_baslik_sablonu": "sabitsiz", "sosyal_linkler": [{"platform": "tiktok", "url": "javascript:x"}], "og_gorsel": {"id": 99999}},
        format="json",
    )
    assert hatali.status_code == 400
    assert {"seo_baslik_sablonu", "sosyal_linkler", "og_gorsel"} <= set(hatali.data)
    assert hatali.data["sosyal_linkler"]["0"].keys() == {"platform", "url"}


def test_silinen_medya_public_ciktida_null(site_istemci, editor_client, sayfa_olustur, medya_olustur):
    medya = medya_olustur()
    sayfa_olustur(
        slug="gorselli",
        bloklar=[{"tip": "gorsel_metin", "veri": {"baslik": "G", "metin": "M", "gorsel": {"id": medya.pk}}}],
        yayinla=True,
    )
    assert site_istemci.get("/api/website/public/sayfalar/gorselli/").data["bloklar"][0]["veri"]["gorsel"]["id"] == medya.pk
    editor_client.patch(f"/api/website/admin/medya/{medya.pk}/", {"alt": "Güncel alt"}, format="json")
    assert site_istemci.get("/api/website/public/sayfalar/gorselli/").data["bloklar"][0]["veri"]["gorsel"]["alt"] == "Güncel alt"
    editor_client.delete(f"/api/website/admin/medya/{medya.pk}/")
    assert site_istemci.get("/api/website/public/sayfalar/gorselli/").data["bloklar"][0]["veri"]["gorsel"] is None


def test_hedef_url_ve_headless_fan_out(settings):
    settings.SITE_REVALIDATE_URLS = ["http://localhost:3000/api/revalidate"]
    settings.SITE_REVALIDATE_HEADLESS_HOST = "eisa-site-headless:3000"
    sahte_dns = [
        (2, 1, 6, "", ("10.42.0.11", 3000)),
        (2, 1, 6, "", ("10.42.0.12", 3000)),
        (2, 1, 6, "", ("10.42.0.11", 3000)),
    ]
    with patch("apps.website.services.revalidate.socket.getaddrinfo", return_value=sahte_dns) as dns:
        urller = rv.hedef_urller()
    dns.assert_called_once()
    assert urller == [
        "http://localhost:3000/api/revalidate",
        "http://10.42.0.11:3000/api/revalidate",
        "http://10.42.0.12:3000/api/revalidate",
    ]


def test_post_govdesi_basligi_ve_hata_toleransi(settings):
    settings.SITE_REVALIDATE_URLS = ["http://a/api/revalidate", "http://b/api/revalidate"]
    settings.REVALIDATE_SECRET = "gizli-secret"
    istekler = []

    def sahte_urlopen(istek, timeout):
        istekler.append((istek, timeout))
        if "//a/" in istek.full_url:
            raise urllib.error.URLError("bağlantı reddedildi")
        yanit = MagicMock()
        yanit.__enter__.return_value = yanit
        return yanit

    with patch("apps.website.services.revalidate.urllib.request.urlopen", side_effect=sahte_urlopen):
        rv.revalidate_gonder(["sayfa:anasayfa", "sayfalar", "site"])  # istisna fırlatmamalı

    assert len(istekler) == 2
    istek, timeout = istekler[1]
    assert timeout == 3
    assert istek.get_method() == "POST"
    assert istek.get_header("X-revalidate-secret") == "gizli-secret"
    assert json.loads(istek.data) == {"tags": ["sayfa:anasayfa", "sayfalar", "site"]}


def test_testlerde_http_cagrisi_yapilmaz():
    assert rv.hedef_urller() == []
