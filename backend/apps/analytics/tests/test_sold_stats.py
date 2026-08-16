"""
Satış istatistikleri testleri.

Kapsam:
  - Admin dashboard satis_sayisi ve en_cok_satilan_etken_madde
  - Eczacı dashboard satis_sayisi ve en_cok_satilan_etken_madde (eczane izolasyonu)
  - Kiosk hareketleri sold filtresi
  - AutoComplete için eczane ve kiosk listelerinin il/ilçe bilgisi döndürmesi
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.analytics.models import OturumLogu, OturumOnerilenEtkenMadde
from apps.lookups.models import Cinsiyet, Il, Ilce, YasAraligi
from apps.lookups.seed import seed_lookups
from apps.pharmacies.models import Eczane, Kiosk
from apps.products.models import EtkenMadde

Kullanici = get_user_model()

ADMIN_DASHBOARD_URL = "/api/analytics/admin-dashboard/"
PHARM_DASHBOARD_URL = "/api/pharmacies/me/dashboard/"
ACTIVITIES_URL = "/api/analytics/kiosk-activities/"
ECZANELER_URL = "/api/pharmacies/"
KIOSKLAR_URL = "/api/pharmacies/kiosks/"


@pytest.fixture(autouse=True)
def _seed(db):
    seed_lookups()


def _make_il_ilce(il_ad="TestIl", ilce_ad="TestIlce"):
    il, _ = Il.objects.get_or_create(ad=il_ad)
    ilce, _ = Ilce.objects.get_or_create(il=il, ad=ilce_ad)
    return il, ilce


def _make_eczane(ad="Eczane", il_ad="TestIl", ilce_ad="TestIlce"):
    il, ilce = _make_il_ilce(il_ad, ilce_ad)
    return Eczane.objects.create(ad=ad, il=il, ilce=ilce)


def _make_kiosk(eczane, ad="Kiosk", mac=None):
    mac = mac or f"AA:{uuid.uuid4().hex[:2].upper()}:CC:DD:EE:FF"
    return Kiosk.objects.create(
        eczane=eczane, ad=ad, mac_adresi=mac,
        uygulama_anahtari=f"key-{mac.replace(':', '')}",
    )


def _make_session(kiosk, sold=None, qr=None, **kwargs):
    age = YasAraligi.objects.first()
    gender = Cinsiyet.objects.first()
    qr = qr or uuid.uuid4().hex[:8].upper()
    return OturumLogu.objects.create(
        kiosk=kiosk, yas_araligi=age, cinsiyet=gender,
        qr_kodu=qr, sold=sold, tamamlandi=True,
        durum=OturumLogu.Durum.COMPLETED, **kwargs
    )


def _make_etken_madde(ad):
    return EtkenMadde.objects.get_or_create(ad=ad)[0]


def _add_ingredient(oturum, em):
    return OturumOnerilenEtkenMadde.objects.create(
        oturum=oturum, etken_madde=em, etken_madde_adi_snapshot=em.ad
    )


def _admin_client():
    user = Kullanici.objects.create_user(
        username=f"sadmin_{uuid.uuid4().hex[:6]}", password="X", rol="superadmin"
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c, user


def _pharm_client(eczane):
    user = Kullanici.objects.create_user(
        username=f"eczaci_{uuid.uuid4().hex[:6]}", password="X",
        rol="pharmacist", eczane=eczane,
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c, user


# ─── Admin Dashboard Satış İstatistikleri ────────────────────────────────────

class TestAdminDashboardSatisSayisi:
    def test_sifir_satis_sifir_doner(self, db):
        client, _ = _admin_client()
        res = client.get(ADMIN_DASHBOARD_URL)
        assert res.status_code == 200
        assert res.data["satis_sayisi"] == 0
        assert res.data["en_cok_satilan_etken_madde"] is None

    def test_satis_sayisi_dogru_hesaplanir(self, db):
        eczane = _make_eczane()
        kiosk = _make_kiosk(eczane)
        _make_session(kiosk, sold=True)
        _make_session(kiosk, sold=True)
        _make_session(kiosk, sold=False)
        _make_session(kiosk, sold=None)

        client, _ = _admin_client()
        res = client.get(ADMIN_DASHBOARD_URL)
        assert res.status_code == 200
        assert res.data["satis_sayisi"] == 2

    def test_en_cok_satilan_etken_madde(self, db):
        eczane = _make_eczane()
        kiosk = _make_kiosk(eczane)
        em_a = _make_etken_madde("Aspirin")
        em_b = _make_etken_madde("Ibuprofen")

        s1 = _make_session(kiosk, sold=True)
        _add_ingredient(s1, em_a)
        _add_ingredient(s1, em_b)

        s2 = _make_session(kiosk, sold=True)
        _add_ingredient(s2, em_a)  # em_a: 2, em_b: 1

        s3 = _make_session(kiosk, sold=False)
        _add_ingredient(s3, em_b)  # sold=False — sayılmaz

        client, _ = _admin_client()
        res = client.get(ADMIN_DASHBOARD_URL)
        assert res.status_code == 200
        em = res.data["en_cok_satilan_etken_madde"]
        assert em is not None
        assert em["ad"] == "Aspirin"
        assert em["sayi"] == 2  # sold=False oturumlar sayılmaz

    def test_tarih_filtresi_satis_sayisini_etkiler(self, db):
        from django.utils.timezone import localdate
        from datetime import timedelta as td
        eczane = _make_eczane()
        kiosk = _make_kiosk(eczane)
        _make_session(kiosk, sold=True)

        today = localdate().isoformat()
        future = (localdate() + td(days=365)).isoformat()

        client, _ = _admin_client()
        # Bugün dahil filtre — kayıt görünmeli
        res = client.get(ADMIN_DASHBOARD_URL, {"start_date": today, "end_date": today})
        assert res.data["satis_sayisi"] >= 1

        # Gelecek tarih filtresi — hiç kayıt yok
        res2 = client.get(ADMIN_DASHBOARD_URL, {"start_date": future, "end_date": future})
        assert res2.data["satis_sayisi"] == 0


# ─── Eczacı Dashboard Satış İstatistikleri ve İzolasyonu ─────────────────────

class TestEczaciDashboardSatisSayisi:
    def test_eczaci_yalniz_kendi_satirini_gorur(self, db):
        eczane_a = _make_eczane("EczA", "Ankara", "Çankaya")
        eczane_b = _make_eczane("EczB", "İstanbul", "Kadıköy")
        kiosk_a = _make_kiosk(eczane_a)
        kiosk_b = _make_kiosk(eczane_b)

        _make_session(kiosk_a, sold=True)
        _make_session(kiosk_a, sold=True)
        _make_session(kiosk_b, sold=True)  # başka eczane

        client, _ = _pharm_client(eczane_a)
        res = client.get(PHARM_DASHBOARD_URL)
        assert res.status_code == 200
        assert res.data["satis_sayisi"] == 2  # sadece kendi eczanesi

    def test_sifir_satis(self, db):
        eczane = _make_eczane()
        client, _ = _pharm_client(eczane)
        res = client.get(PHARM_DASHBOARD_URL)
        assert res.status_code == 200
        assert res.data["satis_sayisi"] == 0
        assert res.data["en_cok_satilan_etken_madde"] is None

    def test_en_cok_satilan_etken_madde_eczane_scope(self, db):
        eczane_a = _make_eczane("EczA2")
        eczane_b = _make_eczane("EczB2")
        kiosk_a = _make_kiosk(eczane_a)
        kiosk_b = _make_kiosk(eczane_b)
        em = _make_etken_madde("Paracetamol")

        s_a = _make_session(kiosk_a, sold=True)
        _add_ingredient(s_a, em)

        # Eczane B'de birden fazla sold session + ingredient — ama eczane A'ya etki etmemeli
        for i in range(3):
            s_b = _make_session(kiosk_b, sold=True, qr=f"SLB{i:04d}")
            _add_ingredient(s_b, em)

        client, _ = _pharm_client(eczane_a)
        res = client.get(PHARM_DASHBOARD_URL)
        assert res.status_code == 200
        em_data = res.data["en_cok_satilan_etken_madde"]
        assert em_data is not None
        assert em_data["sayi"] == 1  # sadece kendi eczanesi (kiosk_a)


# ─── Kiosk Hareketleri sold Filtresi ─────────────────────────────────────────

class TestKioskActivitiesSoldFilter:
    def test_sold_true_filtresi(self, db):
        eczane = _make_eczane()
        kiosk = _make_kiosk(eczane)
        s_sold = _make_session(kiosk, sold=True, qr="SOLD0001")
        _make_session(kiosk, sold=False, qr="NOSL0001")
        _make_session(kiosk, sold=None, qr="NULL0001")

        client, _ = _admin_client()
        res = client.get(ACTIVITIES_URL, {"sold": "true"})
        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "SOLD0001" in qr_list
        assert "NOSL0001" not in qr_list
        assert "NULL0001" not in qr_list

    def test_eczaci_sold_filtresi_eczane_scope(self, db):
        eczane_a = _make_eczane("EczA3")
        eczane_b = _make_eczane("EczB3")
        kiosk_a = _make_kiosk(eczane_a)
        kiosk_b = _make_kiosk(eczane_b)
        _make_session(kiosk_a, sold=True, qr="SLDA0001")
        _make_session(kiosk_b, sold=True, qr="SLDB0001")

        client, _ = _pharm_client(eczane_a)
        res = client.get(ACTIVITIES_URL, {"sold": "true"})
        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "SLDA0001" in qr_list
        assert "SLDB0001" not in qr_list

    def test_sold_etken_madde_adlari_dahil(self, db):
        eczane = _make_eczane()
        kiosk = _make_kiosk(eczane)
        em = _make_etken_madde("Kodein")
        s = _make_session(kiosk, sold=True, qr="EMDL0001")
        _add_ingredient(s, em)

        client, _ = _admin_client()
        res = client.get(ACTIVITIES_URL, {"sold": "true"})
        assert res.status_code == 200
        row = next(r for r in res.data["results"] if r["qr_kodu"] == "EMDL0001")
        assert "Kodein" in row["etken_madde_adlari"]


# ─── AutoComplete: Eczane ve Kiosk listelerinde il/ilçe bilgisi ─────────────

class TestAutoCompleteListeler:
    def test_eczane_listesinde_il_ilce_bilgisi_var(self, db):
        il, ilce = _make_il_ilce("Bursa", "Osmangazi")
        Eczane.objects.create(ad="Test Eczane", il=il, ilce=ilce)

        client, _ = _admin_client()
        res = client.get(ECZANELER_URL)
        assert res.status_code == 200
        items = res.data if isinstance(res.data, list) else res.data.get("results", res.data)
        eczane = next((e for e in items if e["ad"] == "Test Eczane"), None)
        assert eczane is not None
        assert "il_adi" in eczane or "il" in eczane  # il bilgisi mevcut

    def test_kiosk_listesinde_eczane_bilgisi_var(self, db):
        eczane = _make_eczane("Bursa Eczane")
        kiosk = _make_kiosk(eczane, ad="Test Kiosk AC")

        client, _ = _admin_client()
        res = client.get(KIOSKLAR_URL)
        assert res.status_code == 200
        items = res.data if isinstance(res.data, list) else res.data.get("results", res.data)
        k = next((k for k in items if k.get("id") == kiosk.id), None)
        assert k is not None
        # Eczane bağlantısı mevcut (eczane_adi veya eczane alanı)
        assert k.get("eczane_adi") or k.get("eczane") is not None

    def test_eczaci_sadece_kendi_kioskunu_gorur(self, db):
        eczane_a = _make_eczane("EczaneAC1")
        eczane_b = _make_eczane("EczaneAC2")
        _make_kiosk(eczane_a, ad="KioskAC1")
        _make_kiosk(eczane_b, ad="KioskAC2")

        # Pharmacist dashboard sadece kendi eczanesinin kiosklar döner
        client, _ = _pharm_client(eczane_a)
        res = client.get(PHARM_DASHBOARD_URL)
        assert res.status_code == 200
        kiosk_ads = [k["ad"] for k in res.data.get("kiosklar", [])]
        assert "KioskAC1" in kiosk_ads
        assert "KioskAC2" not in kiosk_ads
