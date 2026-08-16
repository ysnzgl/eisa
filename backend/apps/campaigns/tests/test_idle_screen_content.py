"""IdleScreenContent (İçerik Yönetimi) — model, CRUD, validation, catalog testleri.

Kapsam:
  IC-01  Model create + varsayilan aktif
  IC-02  Serializer baslik zorunlu / whitespace reddi
  IC-03  Serializer metin zorunlu / whitespace reddi
  IC-04  Baslik 100 karakter siniri
  IC-05  Metin 300 karakter siniri
  IC-06  SuperAdmin CRUD (list/create/update/delete) 2xx
  IC-07  Yetkisiz erisim reddi (401/403)
  IC-08  Kiosk sync yalniz aktif idle icerikleri doner
  IC-09  HouseAd modeli kaldirildi (import edilemez)
"""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.campaigns.models import IdleScreenContent
from apps.campaigns.serializers import IdleScreenContentSerializer


# ─── IC-01 model ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_ic01_model_create_defaults():
    c = IdleScreenContent.objects.create(baslik="Baslik", metin="Metin")
    assert c.aktif is True
    assert c.olusturulma_tarihi is not None
    assert c.guncellenme_tarihi is not None
    assert str(c) == "Baslik"


# ─── IC-02 / IC-03 zorunlu + whitespace ──────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize("baslik", ["", "   ", "\t\n"])
def test_ic02_baslik_required_whitespace(baslik):
    ser = IdleScreenContentSerializer(data={"baslik": baslik, "metin": "Gecerli metin"})
    assert not ser.is_valid()
    assert "baslik" in ser.errors


@pytest.mark.django_db
@pytest.mark.parametrize("metin", ["", "   ", "\t\n"])
def test_ic03_metin_required_whitespace(metin):
    ser = IdleScreenContentSerializer(data={"baslik": "Gecerli baslik", "metin": metin})
    assert not ser.is_valid()
    assert "metin" in ser.errors


# ─── IC-04 / IC-05 karakter sinirlari ────────────────────────────────────────

@pytest.mark.django_db
def test_ic04_baslik_max_100():
    ser = IdleScreenContentSerializer(data={"baslik": "x" * 101, "metin": "m"})
    assert not ser.is_valid()
    assert "baslik" in ser.errors

    ser_ok = IdleScreenContentSerializer(data={"baslik": "x" * 100, "metin": "m"})
    assert ser_ok.is_valid(), ser_ok.errors


@pytest.mark.django_db
def test_ic05_metin_max_300():
    ser = IdleScreenContentSerializer(data={"baslik": "b", "metin": "m" * 301})
    assert not ser.is_valid()
    assert "metin" in ser.errors

    ser_ok = IdleScreenContentSerializer(data={"baslik": "b", "metin": "m" * 300})
    assert ser_ok.is_valid(), ser_ok.errors


# ─── IC-06 SuperAdmin CRUD ───────────────────────────────────────────────────

@pytest.mark.django_db
def test_ic06_superadmin_crud(admin_client):
    base = "/api/campaigns/v2/idle-contents/"

    # create
    r = admin_client.post(base, {"baslik": "Kahvalti", "metin": "Dengeli beslenin."}, format="json")
    assert r.status_code in (200, 201), r.content
    cid = r.json()["id"]

    # list
    r = admin_client.get(base)
    assert r.status_code == 200
    body = r.json()
    rows = body if isinstance(body, list) else body.get("results", [])
    assert any(row["id"] == cid for row in rows)

    # update
    r = admin_client.patch(f"{base}{cid}/", {"aktif": False}, format="json")
    assert r.status_code == 200
    assert r.json()["aktif"] is False

    # delete
    r = admin_client.delete(f"{base}{cid}/")
    assert r.status_code in (200, 204)
    assert not IdleScreenContent.objects.filter(pk=cid).exists()


# ─── IC-07 yetki ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_ic07_unauthorized_rejected(api_client):
    r = api_client.get("/api/campaigns/v2/idle-contents/")
    assert r.status_code in (401, 403)


# ─── IC-08 kiosk sync yalniz aktif ───────────────────────────────────────────

@pytest.mark.django_db
def test_ic08_kiosk_sync_only_active(kiosk_client):
    IdleScreenContent.objects.create(baslik="Aktif", metin="Gorunur", aktif=True)
    IdleScreenContent.objects.create(baslik="Pasif", metin="Gizli", aktif=False)

    r = kiosk_client.get("/api/kiosk/v1/sync/")
    assert r.status_code == 200
    body = r.json()
    assert "idle_contents" in body
    assert "house_ads" not in body
    basliklar = {c["baslik"] for c in body["idle_contents"]}
    assert "Aktif" in basliklar
    assert "Pasif" not in basliklar
    for c in body["idle_contents"]:
        assert set(c.keys()) >= {"id", "baslik", "metin", "aktif", "updated_at"}


# ─── IC-09 HouseAd kaldirildi ────────────────────────────────────────────────

@pytest.mark.django_db
def test_ic09_house_ad_model_removed():
    with pytest.raises(ImportError):
        from apps.campaigns.models import HouseAd  # noqa: F401
