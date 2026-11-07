"""Önizleme token'ı: geçerli / geçersiz / süresi dolmuş / başka içeriğe ait."""
from unittest.mock import patch

import pytest
from django.core import signing

from apps.core.uow import save_new
from apps.website.models import BlogYazisi
from apps.website.views.preview import onizleme_token_uret

from .conftest import ornek_hero

pytestmark = pytest.mark.django_db


def test_sayfa_onizleme_taslaktan_doner(site_istemci, sayfa_olustur):
    sayfa = sayfa_olustur(
        slug="taslak-sayfa",
        bloklar=[
            {"tip": "hero", "veri": ornek_hero(baslik="Taslak değere", vurgu="değere")},
            {"tip": "sayfa_basligi", "veri": {"baslik": "Gizli"}, "gorunur": False},
        ],
    )
    token = onizleme_token_uret("sayfa", sayfa.slug)
    yanit = site_istemci.get(f"/api/website/preview/sayfalar/{sayfa.slug}/", {"token": token})
    assert yanit.status_code == 200
    assert yanit["Cache-Control"] == "no-store"
    assert set(yanit.data) == {"slug", "baslik", "seo", "yayin_tarihi", "revizyon_id", "bloklar"}
    assert [b["tip"] for b in yanit.data["bloklar"]] == ["hero"]
    assert yanit.data["bloklar"][0]["veri"]["baslik"] == "Taslak değere"
    # Public'te yayında olmadığı için görünmez.
    assert site_istemci.get(f"/api/website/public/sayfalar/{sayfa.slug}/").status_code == 404


def test_gecersiz_ve_baska_icerik_tokeni_403(site_istemci, sayfa_olustur):
    sayfa = sayfa_olustur(slug="gizli")
    yol = f"/api/website/preview/sayfalar/{sayfa.slug}/"
    for token in ("", "bozuk", onizleme_token_uret("sayfa", "baska-sayfa"), onizleme_token_uret("blog", "gizli")):
        yanit = site_istemci.get(yol, {"token": token})
        assert yanit.status_code == 403, token
        assert yanit["Cache-Control"] == "no-store"
    # Farklı salt ile imzalanmış token
    yabanci = signing.TimestampSigner(salt="baska-salt").sign("sayfa:gizli")
    assert site_istemci.get(yol, {"token": yabanci}).status_code == 403


def test_suresi_dolmus_token_403(site_istemci, sayfa_olustur):
    sayfa = sayfa_olustur(slug="eski")
    with patch("django.core.signing.time.time", return_value=1_000_000_000):
        token = onizleme_token_uret("sayfa", sayfa.slug)
    yanit = site_istemci.get(f"/api/website/preview/sayfalar/{sayfa.slug}/", {"token": token})
    assert yanit.status_code == 403


def test_blog_onizleme_taslak_yazi(site_istemci):
    save_new(BlogYazisi(slug="taslak-yazi", baslik="Taslak", durum="taslak", icerik_html="<p>x</p>"))
    yanit = site_istemci.get("/api/website/preview/blog/taslak-yazi/", {"token": onizleme_token_uret("blog", "taslak-yazi")})
    assert yanit.status_code == 200 and yanit["Cache-Control"] == "no-store"
    assert yanit.data["icerik_html"] == "<p>x</p>" and yanit.data["ilgili"] == []
    assert site_istemci.get("/api/website/public/blog/taslak-yazi/").status_code == 404
    olmayan = site_istemci.get("/api/website/preview/blog/yok/", {"token": onizleme_token_uret("blog", "yok")})
    assert olmayan.status_code == 404
