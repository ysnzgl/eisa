"""Site ↔ API app-key: public ve önizleme uçları yalnızca X-Website-Token taşıyan site sunucusuna açıktır."""
import pytest
from django.core.checks import run_checks

from apps.website.models import Basvuru

PUBLIC_UCLAR = [
    "/api/website/public/site/",
    "/api/website/public/sayfalar/",
    "/api/website/public/sayfalar/anasayfa/",
    "/api/website/public/blog/",
    "/api/website/public/blog/herhangi/",
    "/api/website/preview/sayfalar/anasayfa/?token=x",
    "/api/website/preview/blog/herhangi/?token=x",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url", PUBLIC_UCLAR)
def test_tokensiz_dis_istek_404(dis_istemci, url):
    assert dis_istemci.get(url).status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("url", PUBLIC_UCLAR)
def test_yanlis_token_404(dis_istemci, url):
    assert dis_istemci.get(url, HTTP_X_WEBSITE_TOKEN="yanlis-token").status_code == 404


@pytest.mark.django_db
def test_tokensiz_basvuru_404_ve_kayit_yok(dis_istemci):
    yanit = dis_istemci.post(
        "/api/website/public/basvurular/",
        {"tip": "genel", "ad_soyad": "Bot", "eposta": "bot@example.com", "kvkk_onay": True},
        format="json",
    )
    assert yanit.status_code == 404
    assert not Basvuru.objects.exists()


@pytest.mark.django_db
def test_site_sunucusu_erisir(site_istemci):
    assert site_istemci.get("/api/website/public/site/").status_code == 200


@pytest.mark.django_db
def test_admin_uclari_tokenden_etkilenmez(editor_client):
    # Portal (tarayıcı) admin uçlarını JWT ile kullanır; site token'ı gerekmez.
    assert editor_client.get("/api/website/admin/sayfalar/").status_code == 200


def test_uretimde_varsayilan_anahtarlar_uyari_verir(settings):
    settings.DEBUG = False
    settings.WEBSITE_SERVER_TOKEN = "dev-website-token"
    settings.REVALIDATE_SECRET = "kisa"
    kimlikler = {m.id for m in run_checks(tags=["security"]) if m.id.startswith("website.")}
    assert kimlikler == {"website.W001", "website.W002"}

    settings.WEBSITE_SERVER_TOKEN = "x" * 40
    settings.REVALIDATE_SECRET = "y" * 40
    assert not [m for m in run_checks(tags=["security"]) if m.id.startswith("website.")]