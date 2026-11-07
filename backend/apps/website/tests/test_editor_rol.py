"""
Güvenlik: `editor` rolü yalnızca web sitesi modülünü yönetir.

Editor'ün eczacı veya superadmin yetkisi ALMADIĞINI ve hiçbir panel ucunda çökmediğini
doğrulamak için tüm parametresiz GET uçları URL çözümleyicisinden otomatik toplanır ve
editor ile çağrılır. İzin listesindeki (kendi profili, lookup referans verileri, web sitesi)
uçlar dışında 2xx ya da 5xx dönmemelidir.
"""
import re

import pytest
from django.urls import URLPattern, URLResolver, get_resolver, resolve
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import Kullanici

pytestmark = pytest.mark.django_db

IZINLI_ONEKLER = (
    "api/website/",
    "api/users/me/",
    "api/lookups/",
    "api/auth/",
    "api/schema/",
    "api/docs/",
    "api/redoc/",
    "api/destek/parametreler/",  # referans parametre listesi (kişisel/eczane verisi yok)
    "api/analytics/client-events/",  # panel hata log ingest (POST)
    "healthz",
    "readyz",
    "favicon.ico",
    "admin/",
)


def _yol_parcasi(pattern) -> str | None:
    s = str(pattern.pattern)
    if s.startswith("^"):
        s = s[1:]
    if s.endswith("$"):
        s = s[:-1]
    if "<" in s or "(" in s or "\\" in s or "?" in s or "[" in s or "*" in s:
        return None
    return s


def _parametresiz_yollar(patterns=None, onek="") -> list[str]:
    patterns = get_resolver().url_patterns if patterns is None else patterns
    yollar = []
    for p in patterns:
        parca = _yol_parcasi(p)
        if parca is None:
            continue
        if isinstance(p, URLResolver):
            yollar.extend(_parametresiz_yollar(p.url_patterns, onek + parca))
        elif isinstance(p, URLPattern):
            yollar.append(onek + parca)
    return sorted(set(yollar))


@pytest.fixture
def editor_jwt_client(api_client):
    editor = Kullanici.objects.create_user(username="editor_tara", password="Str0ngPass!", rol=Kullanici.Rol.EDITOR)
    token = RefreshToken.for_user(editor).access_token
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


def test_editor_panel_uclarina_erisemez_ve_cokmez(editor_jwt_client, eczane):
    yollar = _parametresiz_yollar()
    assert any(y.startswith("api/website/admin/") for y in yollar)
    sizinti, cokme = [], []
    for yol in yollar:
        # DRF DefaultRouter kök görünümü yalnızca URL listesi döner (veri içermez).
        if getattr(getattr(resolve("/" + yol).func, "cls", None), "__name__", "") == "APIRootView":
            continue
        yanit = editor_jwt_client.get("/" + yol)
        if yanit.status_code >= 500:
            cokme.append((yol, yanit.status_code))
        elif 200 <= yanit.status_code < 300 and not yol.startswith(IZINLI_ONEKLER) and yol not in ("",):
            sizinti.append((yol, yanit.status_code))
    assert not cokme, f"Editor ile çöken uçlar: {cokme}"
    assert not sizinti, f"Editor'ün erişmemesi gereken uçlar: {sizinti}"


def test_editor_eczaci_ve_superadmin_uclarinda_403(editor_jwt_client, eczane):
    for yol in ("/api/users/", "/api/pharmacies/", "/api/destek/talepler/", "/api/products/sync/"):
        yanit = editor_jwt_client.get(yol)
        assert yanit.status_code in (403, 404), (yol, yanit.status_code)


def test_editor_login_ve_me_yaniti(api_client):
    Kullanici.objects.create_user(username="editor_giris", password="Str0ngPass!123", rol=Kullanici.Rol.EDITOR)
    yanit = api_client.post("/api/auth/token/", {"username": "editor_giris", "password": "Str0ngPass!123"}, format="json")
    assert yanit.status_code == 200
    assert yanit.data["rol"] == "editor"
    assert yanit.data["eczane"] is None
    me = api_client.get("/api/users/me/")
    assert me.status_code == 200
    assert me.data["rol"] == "editor"
    assert me.data["eczane"] is None


def test_superadmin_editor_kullanici_olusturabilir_eczane_zorunlu_degil(admin_client, eczane):
    yanit = admin_client.post(
        "/api/users/",
        {"username": "yeni_editor", "password": "Cok-Guclu-Parola-42", "rol": "editor", "email": "e@eisa.com.tr"},
        format="json",
    )
    assert yanit.status_code == 201, yanit.data
    kullanici = Kullanici.objects.get(username="yeni_editor")
    assert kullanici.rol == Kullanici.Rol.EDITOR
    assert kullanici.eczane_id is None

    # Editor'e eczane bağlanamaz (eczane verisine kapsam sızmasın).
    yanit = admin_client.post(
        "/api/users/",
        {"username": "editor2", "password": "Cok-Guclu-Parola-42", "rol": "editor", "eczane": eczane.pk},
        format="json",
    )
    assert yanit.status_code == 201
    assert Kullanici.objects.get(username="editor2").eczane_id is None


def test_url_toplayici_regex_desenlerini_atlar():
    assert _yol_parcasi(type("P", (), {"pattern": "^(?P<pk>[^/.]+)/$"})()) is None
    assert re.match(r"^api/", "api/website/public/site/")
