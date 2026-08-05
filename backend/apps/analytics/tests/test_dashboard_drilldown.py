"""
Son kontrol: dashboard drill-down ve kiosk event outbox entegrasyon testleri.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.analytics.models import OturumLogu
from apps.lookups.models import Cinsiyet, Il, Ilce, YasAraligi
from apps.lookups.seed import seed_lookups
from apps.pharmacies.models import Eczane, Kiosk
from apps.products.models import Kategori

Kullanici = get_user_model()
ACTIVITIES_URL = "/api/analytics/kiosk-activities/"


@pytest.fixture(autouse=True)
def _seed(db):
    seed_lookups()


def _make_kiosk(eczane_ad="DrillKiosk"):
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Kadikoy")
    eczane = Eczane.objects.create(ad=eczane_ad, il=il, ilce=ilce)
    kiosk = Kiosk.objects.create(
        eczane=eczane, ad="Drill Kiosk",
        mac_adresi=f"DD:{uuid.uuid4().hex[:2].upper()}:DD:DD:DD:DD",
        uygulama_anahtari=f"drill-{uuid.uuid4().hex}",
    )
    return kiosk


def _make_session(kiosk, kategori, qr=None, tamamlandi=True):
    age = YasAraligi.objects.first()
    gender = Cinsiyet.objects.first()
    qr = qr or uuid.uuid4().hex[:8].upper()
    durum = OturumLogu.Durum.COMPLETED if tamamlandi else OturumLogu.Durum.ABANDONED
    return OturumLogu.objects.create(
        kiosk=kiosk, yas_araligi=age, cinsiyet=gender,
        qr_kodu=qr, kategori=kategori, tamamlandi=tamamlandi, durum=durum,
    )


def _admin_client():
    admin = Kullanici.objects.create_user(
        username=f"drill_admin_{uuid.uuid4().hex[:6]}",
        password="X", rol="superadmin",
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(admin).access_token}")
    return c


class TestKategoriSlugFilter:
    """Admin dashboard donut tıklaması → ?kategori_slug= filtresinin çalıştığını doğrular."""

    def test_kategori_slug_filters_sessions(self, db):
        kiosk = _make_kiosk("KatEczane")
        uyku = Kategori.objects.get_or_create(ad="Uyku", slug="uyku")[0]
        agri = Kategori.objects.get_or_create(ad="Agri", slug="agri")[0]

        _make_session(kiosk, uyku, qr="UYKU0001")
        _make_session(kiosk, agri, qr="AGRI0001")

        res = _admin_client().get(ACTIVITIES_URL, {"kategori_slug": "uyku"})
        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "UYKU0001" in qr_list
        assert "AGRI0001" not in qr_list

    def test_kategori_slug_with_date_and_durum(self, db):
        """Birden fazla filtre (slug + tarih + durum) birlikte çalışmalı."""
        from django.utils.timezone import localdate
        kiosk = _make_kiosk("MultiEczane")
        uyku = Kategori.objects.get_or_create(ad="Uyku2", slug="uyku2")[0]

        _make_session(kiosk, uyku, qr="UYKU0010", tamamlandi=True)  # COMPLETED
        _make_session(kiosk, uyku, qr="UYKU0011", tamamlandi=False)  # ABANDONED

        today = localdate()
        res = _admin_client().get(ACTIVITIES_URL, {
            "kategori_slug": "uyku2",
            "durum": "COMPLETED",
            "start_date": str(today),
            "end_date": str(today),
        })
        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "UYKU0010" in qr_list
        assert "UYKU0011" not in qr_list

    def test_unknown_kategori_slug_returns_empty(self, db):
        kiosk = _make_kiosk("EmptyEczane")
        res = _admin_client().get(ACTIVITIES_URL, {"kategori_slug": "nonexistent-slug"})
        assert res.status_code == 200
        assert res.data["count"] == 0

    def test_no_slug_returns_all(self, db):
        kiosk = _make_kiosk("AllEczane")
        uyku = Kategori.objects.get_or_create(ad="UykuAll", slug="uyku-all")[0]
        agri = Kategori.objects.get_or_create(ad="AgriAll", slug="agri-all")[0]
        _make_session(kiosk, uyku, qr="ALL00001")
        _make_session(kiosk, agri, qr="ALL00002")

        res = _admin_client().get(ACTIVITIES_URL)
        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "ALL00001" in qr_list
        assert "ALL00002" in qr_list
