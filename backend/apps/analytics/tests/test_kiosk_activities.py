"""
Kiosk hareketleri endpointleri için testler.

Kapsam:
  - GET /api/analytics/kiosk-activities/ — eczane izolasyonu, admin erişimi,
    durum/tarih/oturum_tipi filtreleri, EXPIRED türetimi, pagination
  - GET /api/analytics/campaign-impressions/ — PlayLog listesi, eczane scope
  - POST /api/kiosk/v1/sessions/ — durum ve cihaz/sunucu zamani ingest
  - Yetkisiz doğrudan kayıt erişimi
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
from apps.campaigns.models import Campaign, Creative, PlayLog
from apps.lookups.models import Cinsiyet, Il, Ilce, YasAraligi
from apps.lookups.seed import seed_lookups
from apps.pharmacies.models import Eczane, Kiosk

ACTIVITIES_URL = "/api/analytics/kiosk-activities/"
IMPRESSIONS_URL = "/api/analytics/campaign-impressions/"

Kullanici = get_user_model()


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _seed(db):
    seed_lookups()


def _make_eczane(ad="Eczane A"):
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Kadikoy")
    return Eczane.objects.create(ad=ad, il=il, ilce=ilce)


def _make_kiosk(eczane, mac="AA:BB:CC:DD:EE:FF"):
    return Kiosk.objects.create(
        eczane=eczane,
        ad="Test Kiosk",
        mac_adresi=mac,
        uygulama_anahtari=f"key-{mac.replace(':','')}",
    )


def _make_session(kiosk, qr=None, tamamlandi=True, hassas=False, **kwargs):
    age = YasAraligi.objects.first()
    gender = Cinsiyet.objects.first()
    qr = qr or uuid.uuid4().hex[:8].upper()
    durum = OturumLogu.Durum.COMPLETED if tamamlandi else OturumLogu.Durum.ABANDONED
    return OturumLogu.objects.create(
        kiosk=kiosk,
        yas_araligi=age,
        cinsiyet=gender,
        qr_kodu=qr,
        hassas_akis=hassas,
        tamamlandi=tamamlandi,
        durum=durum,
        **kwargs,
    )


def _auth_client(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


# ─── Eczane izolasyonu ────────────────────────────────────────────────────────

class TestEczaneIzolasyonu:
    def test_eczaci_yalniz_kendi_verisini_gorur(self, db):
        eczane_a = _make_eczane("Eczane A")
        eczane_b = _make_eczane("Eczane B")
        kiosk_a = _make_kiosk(eczane_a, "A0:A0:A0:A0:A0:A0")
        kiosk_b = _make_kiosk(eczane_b, "B0:B0:B0:B0:B0:B0")

        _make_session(kiosk_a, qr="ECZA0001")
        _make_session(kiosk_b, qr="ECZA0002")

        user = Kullanici.objects.create_user(
            username="eczaci_a", password="X", rol="pharmacist", eczane=eczane_a
        )
        res = _auth_client(user).get(ACTIVITIES_URL)

        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "ECZA0001" in qr_list
        assert "ECZA0002" not in qr_list

    def test_eczaci_baska_eczane_id_ile_sorgu_yapamaz(self, db):
        """URL/query parametresini değiştirerek başka eczanenin verisine erişilmemeli."""
        eczane_a = _make_eczane("Eczane A2")
        eczane_b = _make_eczane("Eczane B2")
        kiosk_b = _make_kiosk(eczane_b, "C0:C0:C0:C0:C0:C0")
        _make_session(kiosk_b, qr="HACK0001")

        user = Kullanici.objects.create_user(
            username="eczaci_a2", password="X", rol="pharmacist", eczane=eczane_a
        )
        # Admin-only eczane_id parametresi eczacı için görmezden gelinmeli
        res = _auth_client(user).get(ACTIVITIES_URL, {"eczane_id": eczane_b.id})

        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "HACK0001" not in qr_list

    def test_eczane_bagli_olmayan_eczaci_bos_liste(self, db):
        user = Kullanici.objects.create_user(
            username="eczaci_noeczane", password="X", rol="pharmacist", eczane=None
        )
        res = _auth_client(user).get(ACTIVITIES_URL)
        assert res.status_code == 200
        assert res.data["count"] == 0

    def test_yetkisiz_erisim_401(self, db):
        res = APIClient().get(ACTIVITIES_URL)
        assert res.status_code == 401


# ─── Admin erişimi ────────────────────────────────────────────────────────────

class TestAdminErisimi:
    def test_admin_tum_kiosklar_gorur(self, db):
        eczane_a = _make_eczane("Admin Eczane A")
        eczane_b = _make_eczane("Admin Eczane B")
        kiosk_a = _make_kiosk(eczane_a, "D0:D0:D0:D0:D0:D0")
        kiosk_b = _make_kiosk(eczane_b, "E0:E0:E0:E0:E0:E0")
        _make_session(kiosk_a, qr="ADM00001")
        _make_session(kiosk_b, qr="ADM00002")

        admin = Kullanici.objects.create_user(username="adm1", password="X", rol="superadmin")
        res = _auth_client(admin).get(ACTIVITIES_URL)

        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "ADM00001" in qr_list
        assert "ADM00002" in qr_list

    def test_admin_eczane_id_filtresi(self, db):
        eczane_a = _make_eczane("Admin EA")
        eczane_b = _make_eczane("Admin EB")
        kiosk_a = _make_kiosk(eczane_a, "F0:F0:F0:F0:F0:F0")
        kiosk_b = _make_kiosk(eczane_b, "G0:G0:G0:G0:G0:G0")
        _make_session(kiosk_a, qr="FILT0001")
        _make_session(kiosk_b, qr="FILT0002")

        admin = Kullanici.objects.create_user(username="adm2", password="X", rol="superadmin")
        res = _auth_client(admin).get(ACTIVITIES_URL, {"eczane_id": eczane_a.id})

        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "FILT0001" in qr_list
        assert "FILT0002" not in qr_list


# ─── Durum filtreleri ─────────────────────────────────────────────────────────

class TestDurumFiltreleri:
    def test_completed_filtresi(self, db, eczane, kiosk):
        _make_session(kiosk, qr="COMP0001", tamamlandi=True)
        _make_session(kiosk, qr="ABND0001", tamamlandi=False)

        admin = Kullanici.objects.create_user(username="adm_d1", password="X", rol="superadmin")
        res = _auth_client(admin).get(ACTIVITIES_URL, {"durum": "COMPLETED"})

        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "COMP0001" in qr_list
        assert "ABND0001" not in qr_list

    def test_abandoned_filtresi(self, db, eczane, kiosk):
        _make_session(kiosk, qr="COMP0002", tamamlandi=True)
        _make_session(kiosk, qr="ABND0002", tamamlandi=False)

        admin = Kullanici.objects.create_user(username="adm_d2", password="X", rol="superadmin")
        res = _auth_client(admin).get(ACTIVITIES_URL, {"durum": "ABANDONED"})

        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "ABND0002" in qr_list
        assert "COMP0002" not in qr_list

    def test_expired_filtresi_read_time_turetimi(self, db, eczane, kiosk):
        """EXPIRED = COMPLETED + danisma_tamamlandi=False + olusturulma_tarihi > 30 dk önce."""
        eski_zaman = timezone.now() - timedelta(minutes=40)
        oturum = _make_session(kiosk, qr="EXPI0001", tamamlandi=True, danisma_tamamlandi=False)
        # Manually set created time to 40 minutes ago (simulate old session)
        OturumLogu.objects.filter(pk=oturum.pk).update(olusturulma_tarihi=eski_zaman)

        # Yeni oturum — EXPIRED sayılmaz (yeni oluşturuldu)
        _make_session(kiosk, qr="EXPI0002", tamamlandi=True, danisma_tamamlandi=False)

        admin = Kullanici.objects.create_user(username="adm_exp", password="X", rol="superadmin")
        res = _auth_client(admin).get(ACTIVITIES_URL, {"durum": "EXPIRED"})

        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "EXPI0001" in qr_list
        assert "EXPI0002" not in qr_list


# ─── Tarih aralığı filtresi ───────────────────────────────────────────────────

class TestTarihFiltreleri:
    def test_start_date_end_date(self, db, eczane, kiosk):
        from django.utils.timezone import localdate

        # "Eski" oturum — 10 gün öncesine ait
        s_old = _make_session(kiosk, qr="OLD00001")
        ten_days_ago = timezone.now() - timedelta(days=10)
        OturumLogu.objects.filter(pk=s_old.pk).update(olusturulma_tarihi=ten_days_ago)

        # "Bugün" oturumu — güncel zaman (Istanbul local date ile eşleşecek)
        _make_session(kiosk, qr="TODAY001")

        today = localdate()   # Europe/Istanbul locale tarihini kullan
        admin = Kullanici.objects.create_user(username="adm_t1", password="X", rol="superadmin")
        res = _auth_client(admin).get(
            ACTIVITIES_URL, {"start_date": str(today), "end_date": str(today)}
        )
        assert res.status_code == 200
        qr_list = [r["qr_kodu"] for r in res.data["results"]]
        assert "TODAY001" in qr_list
        assert "OLD00001" not in qr_list


# ─── Oturum ingest — durum ve zaman ayrımı ───────────────────────────────────

class TestOturumIngest:
    def test_completed_oturum_durum_set(self, db, kiosk, kiosk_client):
        """POST /api/kiosk/v1/sessions/ → tamamlandi=True → durum=COMPLETED."""
        payload = {
            "items": [
                {
                    "idempotency_anahtari": str(uuid.uuid4()),
                    "yas_araligi_kod": YasAraligi.objects.first().kod,
                    "cinsiyet_kod": Cinsiyet.objects.first().kod,
                    "kategori_slug": _ensure_kategori().slug,
                    "hassas_akis": False,
                    "cevaplar": {},
                    "onerilen_etken_maddeler": [],
                    "tamamlandi": True,
                }
            ]
        }
        res = kiosk_client.post("/api/kiosk/v1/sessions/", payload, format="json")
        assert res.status_code == 200
        qr = res.data["results"][0]["qr_kodu"]
        oturum = OturumLogu.objects.get(qr_kodu=qr)
        assert oturum.durum == OturumLogu.Durum.COMPLETED
        assert oturum.tamamlandi is True
        assert oturum.sunucu_zamani is not None

    def test_abandoned_oturum_durum_set(self, db, kiosk, kiosk_client):
        """POST /api/kiosk/v1/sessions/ → tamamlandi=False → durum=ABANDONED."""
        payload = {
            "items": [
                {
                    "idempotency_anahtari": str(uuid.uuid4()),
                    "yas_araligi_kod": YasAraligi.objects.first().kod,
                    "cinsiyet_kod": Cinsiyet.objects.first().kod,
                    "kategori_slug": _ensure_kategori().slug,
                    "hassas_akis": False,
                    "cevaplar": {},
                    "onerilen_etken_maddeler": [],
                    "tamamlandi": False,
                }
            ]
        }
        res = kiosk_client.post("/api/kiosk/v1/sessions/", payload, format="json")
        assert res.status_code == 200
        idem_key = res.data["results"][0]["idempotency_key"]
        oturum = OturumLogu.objects.get(idempotency_anahtari=idem_key)
        assert oturum.durum == OturumLogu.Durum.ABANDONED
        assert oturum.tamamlandi is False

    def test_cihaz_zamani_set_from_olusturulma_tarihi_param(self, db, kiosk, kiosk_client):
        """Kiosk gönderdiği olusturulma_tarihi → cihaz_zamani'na kaydedilir."""
        kiosk_time = "2026-07-01T10:00:00Z"
        payload = {
            "items": [
                {
                    "idempotency_anahtari": str(uuid.uuid4()),
                    "yas_araligi_kod": YasAraligi.objects.first().kod,
                    "cinsiyet_kod": Cinsiyet.objects.first().kod,
                    "kategori_slug": _ensure_kategori().slug,
                    "hassas_akis": False,
                    "cevaplar": {},
                    "onerilen_etken_maddeler": [],
                    "tamamlandi": True,
                    "olusturulma_tarihi": kiosk_time,
                }
            ]
        }
        res = kiosk_client.post("/api/kiosk/v1/sessions/", payload, format="json")
        assert res.status_code == 200
        qr = res.data["results"][0]["qr_kodu"]
        oturum = OturumLogu.objects.get(qr_kodu=qr)
        # cihaz_zamani = kiosk's reported time
        assert oturum.cihaz_zamani is not None
        assert oturum.cihaz_zamani.year == 2026
        assert oturum.cihaz_zamani.month == 7
        # sunucu_zamani = server time (different from kiosk time)
        assert oturum.sunucu_zamani is not None
        assert oturum.sunucu_zamani.year == 2026

    def test_idempotent_tekrar_gonderim_durum_degismez(self, db, kiosk, kiosk_client):
        """Aynı idempotency_anahtari tekrar gönderildiğinde durum değişmemeli."""
        idem = str(uuid.uuid4())
        payload = {
            "items": [
                {
                    "idempotency_anahtari": idem,
                    "yas_araligi_kod": YasAraligi.objects.first().kod,
                    "cinsiyet_kod": Cinsiyet.objects.first().kod,
                    "kategori_slug": _ensure_kategori().slug,
                    "hassas_akis": False,
                    "cevaplar": {},
                    "onerilen_etken_maddeler": [],
                    "tamamlandi": True,
                }
            ]
        }
        res1 = kiosk_client.post("/api/kiosk/v1/sessions/", payload, format="json")
        res2 = kiosk_client.post("/api/kiosk/v1/sessions/", payload, format="json")

        assert res1.status_code == 200
        assert res2.status_code == 200
        assert res2.data["results"][0]["status"] == "existing"
        # Yalnız 1 kayıt oluşmuş olmalı
        assert OturumLogu.objects.filter(idempotency_anahtari=idem).count() == 1


# ─── Campaign impression endpointi ───────────────────────────────────────────

class TestCampaignImpressions:
    def test_eczaci_yalniz_kendi_impression_gorur(self, db):
        eczane_a = _make_eczane("Imp Eczane A")
        eczane_b = _make_eczane("Imp Eczane B")
        kiosk_a = _make_kiosk(eczane_a, "I0:I0:I0:I0:I0:I0")
        kiosk_b = _make_kiosk(eczane_b, "J0:J0:J0:J0:J0:J0")

        _make_play_log(kiosk_a)
        _make_play_log(kiosk_b)

        user = Kullanici.objects.create_user(
            username="imp_eczaci", password="X", rol="pharmacist", eczane=eczane_a
        )
        res = _auth_client(user).get(IMPRESSIONS_URL)

        assert res.status_code == 200
        kiosk_ids = {r["kiosk_id"] for r in res.data["results"]}
        assert kiosk_ids == {kiosk_a.id}

    def test_admin_tum_impressionlari_gorur(self, db):
        eczane_a = _make_eczane("Imp Admin A")
        eczane_b = _make_eczane("Imp Admin B")
        kiosk_a = _make_kiosk(eczane_a, "K0:K0:K0:K0:K0:K0")
        kiosk_b = _make_kiosk(eczane_b, "L0:L0:L0:L0:L0:L0")
        _make_play_log(kiosk_a)
        _make_play_log(kiosk_b)

        admin = Kullanici.objects.create_user(username="imp_admin", password="X", rol="superadmin")
        res = _auth_client(admin).get(IMPRESSIONS_URL)

        assert res.status_code == 200
        kiosk_ids = {r["kiosk_id"] for r in res.data["results"]}
        assert kiosk_a.id in kiosk_ids
        assert kiosk_b.id in kiosk_ids

    def test_campaign_id_filtresi(self, db):
        eczane = _make_eczane("Imp Camp Eczane")
        kiosk = _make_kiosk(eczane, "M0:M0:M0:M0:M0:M0")

        camp_a, creative_a = _make_campaign_creative(kiosk)
        camp_b, creative_b = _make_campaign_creative(kiosk)

        PlayLog.objects.create(kiosk=kiosk, creative=creative_a,
                               played_at=timezone.now(), duration_played=15)
        PlayLog.objects.create(kiosk=kiosk, creative=creative_b,
                               played_at=timezone.now(), duration_played=15)

        admin = Kullanici.objects.create_user(username="imp_camp", password="X", rol="superadmin")
        res = _auth_client(admin).get(IMPRESSIONS_URL, {"campaign_id": str(camp_a.id)})

        assert res.status_code == 200
        camp_ids = {r["campaign_id"] for r in res.data["results"]}
        assert str(camp_a.id) in camp_ids
        assert str(camp_b.id) not in camp_ids


# ─── Pagination ───────────────────────────────────────────────────────────────

class TestPagination:
    def test_response_has_count_next_prev(self, db, eczane, kiosk):
        for i in range(3):
            _make_session(kiosk, qr=f"PAG{i:05d}")

        admin = Kullanici.objects.create_user(username="adm_pag", password="X", rol="superadmin")
        res = _auth_client(admin).get(ACTIVITIES_URL, {"page_size": 2})

        assert res.status_code == 200
        assert "count" in res.data
        assert "next" in res.data
        assert "results" in res.data
        assert len(res.data["results"]) == 2


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _ensure_kategori():
    from apps.products.models import Kategori
    return Kategori.objects.get_or_create(ad="Uyku", slug="uyku")[0]


def _make_play_log(kiosk):
    camp, creative = _make_campaign_creative(kiosk)
    return PlayLog.objects.create(
        kiosk=kiosk, creative=creative, played_at=timezone.now(), duration_played=15
    )


def _make_campaign_creative(kiosk):
    from django.utils import timezone as tz
    camp = Campaign.objects.create(
        name=f"Camp {uuid.uuid4().hex[:6]}",
        start_date=tz.now() - timedelta(days=1),
        end_date=tz.now() + timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )
    creative = Creative.objects.create(
        campaign=camp,
        media_url="https://example.com/ad.mp4",
        duration_seconds=15,
    )
    return camp, creative
