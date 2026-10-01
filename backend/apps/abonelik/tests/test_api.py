"""Abonelik API sözleşmesi testleri (nested oluşturma, uzatma, badge alanları)."""
import datetime as dt

import pytest

from apps.abonelik.models import Sozlesme
from apps.pharmacies.models import Eczane


@pytest.fixture
def il_ilce(db):
    from apps.lookups.models import Il, Ilce
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Kadikoy")
    return il, ilce


def test_eczane_nested_sozlesme_ile_olusur(admin_client, il_ilce):
    il, ilce = il_ilce
    payload = {
        "ad": "Nested Eczane", "il": il.id, "ilce": ilce.id, "sahip_adi": "X",
        "sozlesme": {
            "tur": "STANDART", "sozlesme_tipi_ay": 24,
            "baslangic_tarihi": "2026-01-01", "durum": "AKTIF",
        },
    }
    r = admin_client.post("/api/pharmacies/", payload, format="json")
    assert r.status_code == 201, r.content
    eczane = Eczane.objects.get(ad="Nested Eczane")
    assert eczane.sozlesmeler.filter(durum="AKTIF").count() == 1


def test_eczane_demo_nested_sozlesme(admin_client, il_ilce):
    il, ilce = il_ilce
    payload = {
        "ad": "Demo Eczane", "il": il.id, "ilce": ilce.id, "sahip_adi": "Y",
        "sozlesme": {"tur": "DEMO", "demo_gun": 30, "baslangic_tarihi": "2026-01-01"},
    }
    r = admin_client.post("/api/pharmacies/", payload, format="json")
    assert r.status_code == 201, r.content
    s = Eczane.objects.get(ad="Demo Eczane").sozlesmeler.get()
    assert s.tur == "DEMO" and s.demo_gun == 30


def test_eczane_demo_31_gun_reddedilir(admin_client, il_ilce):
    il, ilce = il_ilce
    payload = {
        "ad": "Bad Demo", "il": il.id, "ilce": ilce.id, "sahip_adi": "Z",
        "sozlesme": {"tur": "DEMO", "demo_gun": 31, "baslangic_tarihi": "2026-01-01"},
    }
    r = admin_client.post("/api/pharmacies/", payload, format="json")
    assert r.status_code == 400


def test_eczane_listesi_badge_alanlari(admin_client, eczane):
    Sozlesme.objects.create(
        eczane=eczane, tur=Sozlesme.Tur.DEMO, demo_gun=20,
        baslangic_tarihi=dt.date.today(), durum=Sozlesme.Durum.AKTIF,
    )
    r = admin_client.get("/api/pharmacies/")
    assert r.status_code == 200
    rows = r.json()
    row = next(x for x in rows if x["id"] == eczane.id)
    assert row["odeme_durumu"] == "DEMO"
    assert row["aktif_sozlesme"]["tur"] == "DEMO"


def test_sozlesme_uzat_endpoint(admin_client, eczane):
    s = Sozlesme.objects.create(
        eczane=eczane, sozlesme_tipi_ay=24,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.AKTIF,
    )
    r = admin_client.post(f"/api/abonelik/sozlesmeler/{s.id}/uzat/",
                          {"ek_ay": 6, "neden": "Uzatma"}, format="json")
    assert r.status_code == 200, r.content
    s.refresh_from_db()
    assert s.ek_ay_toplam == 6


def test_sozlesme_gecmis_endpoint(admin_client, eczane):
    s = Sozlesme.objects.create(
        eczane=eczane, sozlesme_tipi_ay=24,
        baslangic_tarihi=dt.date(2026, 1, 1), durum=Sozlesme.Durum.AKTIF,
    )
    admin_client.post(f"/api/abonelik/sozlesmeler/{s.id}/uzat/",
                      {"ek_ay": 3}, format="json")
    r = admin_client.get(f"/api/abonelik/sozlesmeler/{s.id}/gecmis/")
    assert r.status_code == 200
    data = r.json()
    assert len(data["uzatmalar"]) == 1
    assert len(data["sozlesmeler"]) >= 1
