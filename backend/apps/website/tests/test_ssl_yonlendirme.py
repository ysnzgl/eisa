"""Cluster içi HTTP: sitenin okuduğu uçlar prod'daki HTTPS yönlendirmesinden muaf olmalı."""
import pytest
from django.test import override_settings


@pytest.mark.django_db
@override_settings(SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
def test_public_ve_onizleme_uclari_http_ile_yonlendirilmez(client, settings):
    token = {"HTTP_X_WEBSITE_TOKEN": settings.WEBSITE_SERVER_TOKEN}
    yanit = client.get("/api/website/public/sayfalar/", **token)
    assert yanit.status_code == 200

    # Önizleme ucu yönlendirilmez; geçersiz token 403 döner (301 değil).
    yanit = client.get("/api/website/preview/sayfalar/anasayfa/?token=gecersiz", **token)
    assert yanit.status_code == 403


@pytest.mark.django_db
@override_settings(SECURE_SSL_REDIRECT=True, SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
def test_admin_uclari_https_yonlendirmesine_tabi(client):
    yanit = client.get("/api/website/admin/sayfalar/")
    assert yanit.status_code == 301
    assert yanit["Location"].startswith("https://")