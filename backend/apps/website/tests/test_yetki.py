"""Admin API yetki matrisi: site_istemci / eczacı / editor / superadmin."""
import pytest

pytestmark = pytest.mark.django_db

ADMIN_GET_UCLARI = [
    "/api/website/admin/ayarlar/",
    "/api/website/admin/blok-tipleri/",
    "/api/website/admin/menuler/",
    "/api/website/admin/sayfalar/",
    "/api/website/admin/blog/kategoriler/",
    "/api/website/admin/blog/yazilar/",
    "/api/website/admin/medya/",
    "/api/website/admin/basvurular/",
    "/api/website/admin/basvurular/ozet/",
]


@pytest.mark.parametrize("yol", ADMIN_GET_UCLARI)
def test_anonim_admin_uclarina_erisemez(site_istemci, yol):
    assert site_istemci.get(yol).status_code == 401


@pytest.mark.parametrize("yol", ADMIN_GET_UCLARI)
def test_eczaci_admin_uclarina_erisemez(eczaci_api, yol):
    assert eczaci_api.get(yol).status_code == 403


@pytest.mark.parametrize("yol", ADMIN_GET_UCLARI)
def test_editor_admin_uclarina_erisir(editor_client, yol):
    assert editor_client.get(yol).status_code == 200


@pytest.mark.parametrize("yol", ADMIN_GET_UCLARI)
def test_superadmin_admin_uclarina_erisir(superadmin_client, yol):
    assert superadmin_client.get(yol).status_code == 200


def test_eczaci_yazamaz(eczaci_api):
    yanit = eczaci_api.post("/api/website/admin/sayfalar/", {"slug": "x", "baslik": "X"}, format="json")
    assert yanit.status_code == 403


def test_pasif_editor_erisemez(editor_client, editor):
    editor.is_active = False
    editor.save(update_fields=["is_active"])
    assert editor_client.get("/api/website/admin/sayfalar/").status_code == 403


def test_public_uclar_jwt_cerezinden_etkilenmez(site_istemci, sayfa_olustur):
    """Bozuk/süresi dolmuş panel çerezi public uçları 401'e düşürmemeli (authentication_classes=[])."""
    sayfa_olustur(slug="anasayfa", yayinla=True)
    site_istemci.cookies["eisa_access"] = "bozuk.jwt.token"
    assert site_istemci.get("/api/website/public/site/").status_code == 200
    assert site_istemci.get("/api/website/public/sayfalar/anasayfa/").status_code == 200
