"""
PharmacyCampaign feed endpoint ve serializer testleri.

PC-01..05: Orijinal testler (eczane hedefleme, aktiflik, auth)
PC-06..07: duration_seconds validasyonu (15/30/60 izinli; diğerleri reddedilir)
PC-08..11: İl/ilçe/eczane hedefleme (OR mantığı)
PC-12: Çok hedef koşulu — distinct (tek kayıt döner)
PC-13: Hiç hedefi olmayan kampanya feed'e girmez
"""
from __future__ import annotations

import datetime as _dt

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.campaigns.models import PharmacyCampaign
from apps.lookups.models import Il, Ilce
from apps.pharmacies.models import Eczane
from apps.users.models import Kullanici


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def il(db):
    il, _ = Il.objects.get_or_create(ad="Test İl")
    return il


@pytest.fixture
def il_baska(db):
    il, _ = Il.objects.get_or_create(ad="Başka İl")
    return il


@pytest.fixture
def ilce(db, il):
    ilce, _ = Ilce.objects.get_or_create(il=il, ad="Test İlçe")
    return ilce


@pytest.fixture
def ilce_baska(db, il_baska):
    ilce, _ = Ilce.objects.get_or_create(il=il_baska, ad="Başka İlçe")
    return ilce


@pytest.fixture
def eczane_a(db, il, ilce):
    return Eczane.objects.create(ad="Eczane A", aktif=True, il=il, ilce=ilce)


@pytest.fixture
def eczane_b(db, il_baska, ilce_baska):
    return Eczane.objects.create(ad="Eczane B", aktif=True, il=il_baska, ilce=ilce_baska)


@pytest.fixture
def eczaci_a(db, eczane_a):
    return Kullanici.objects.create_user(
        username="eczaci_a", password="pass", rol=Kullanici.Rol.ECZACI, eczane=eczane_a,
    )


@pytest.fixture
def eczaci_no_eczane(db):
    return Kullanici.objects.create_user(
        username="eczaci_noec", password="pass", rol=Kullanici.Rol.ECZACI, eczane=None,
    )


def _make_campaign(name, *, pharmacies=(), iller=(), ilceler=(), active=True,
                   offset_days=(-1, 30), duration=15):
    now = timezone.now()
    c = PharmacyCampaign.objects.create(
        name=name,
        media_url="https://files.eisa.com.tr/eisa-files/ads/test.jpg",
        start_at=now + _dt.timedelta(days=offset_days[0]),
        end_at=now + _dt.timedelta(days=offset_days[1]),
        duration_seconds=duration,
        is_active=active,
    )
    if pharmacies:
        c.target_pharmacies.set(pharmacies)
    if iller:
        c.target_iller.set(iller)
    if ilceler:
        c.target_ilceler.set(ilceler)
    return c


FEED_URL = "/api/campaigns/v2/pharmacy-campaigns/feed/"


# ─── PC-01..05: Temel testler ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_pc01_pharmacist_gets_own_pharmacy_campaigns(eczaci_a, eczane_a, eczane_b):
    """Eczacı yalnızca kendi eczanesine hedeflenmiş kampanyaları alır."""
    camp = _make_campaign("A Kampanya", pharmacies=[eczane_a])
    _    = _make_campaign("B Kampanya", pharmacies=[eczane_b])

    client = APIClient()
    client.force_authenticate(user=eczaci_a)
    resp = client.get(FEED_URL)

    assert resp.status_code == 200
    ids = {c["id"] for c in resp.data}
    assert str(camp.id) in ids
    assert len(ids) == 1


@pytest.mark.django_db
def test_pc02_inactive_or_expired_excluded(eczaci_a, eczane_a):
    """Pasif/süresi geçmiş/henüz başlamamış kampanyalar feed'e girmez."""
    _make_campaign("Pasif", pharmacies=[eczane_a], active=False)
    _make_campaign("Geçmiş", pharmacies=[eczane_a], offset_days=(-30, -1))
    _make_campaign("Gelecek", pharmacies=[eczane_a], offset_days=(5, 30))

    client = APIClient()
    client.force_authenticate(user=eczaci_a)
    resp = client.get(FEED_URL)
    assert resp.status_code == 200
    assert resp.data == []


@pytest.mark.django_db
def test_pc03_no_eczane_returns_empty(eczaci_no_eczane, eczane_a):
    """Eczanesi olmayan eczacı boş liste alır."""
    _make_campaign("X", pharmacies=[eczane_a])
    client = APIClient()
    client.force_authenticate(user=eczaci_no_eczane)
    resp = client.get(FEED_URL)
    assert resp.status_code == 200
    assert resp.data == []


@pytest.mark.django_db
def test_pc04_feed_fields_only(eczaci_a, eczane_a):
    """Feed yalnızca id/name/media_url/duration_seconds içerir."""
    _make_campaign("T", pharmacies=[eczane_a])
    client = APIClient()
    client.force_authenticate(user=eczaci_a)
    resp = client.get(FEED_URL)
    assert resp.status_code == 200
    assert resp.data
    assert set(resp.data[0].keys()) == {"id", "name", "media_url", "duration_seconds"}


@pytest.mark.django_db
def test_pc05_unauthenticated_returns_403(db):
    """Kimliksiz istek 401/403 döner."""
    client = APIClient()
    assert client.get(FEED_URL).status_code in (401, 403)


# ─── PC-06..07: duration_seconds validasyonu ─────────────────────────────────

@pytest.mark.django_db
@pytest.mark.parametrize("dur", [15, 30, 60])
def test_pc06_allowed_durations_accepted(eczane_a, dur):
    """15, 30, 60 saniye kabul edilir."""
    c = PharmacyCampaign.objects.create(
        name=f"dur_{dur}",
        media_url="https://files.eisa.com.tr/eisa-files/ads/test.jpg",
        start_at=timezone.now(),
        end_at=timezone.now() + _dt.timedelta(days=10),
        duration_seconds=dur,
    )
    c.target_pharmacies.set([eczane_a])
    assert c.duration_seconds == dur


@pytest.mark.django_db
@pytest.mark.parametrize("bad_dur", [10, 20, 45, 90, 120])
def test_pc07_invalid_durations_rejected_by_serializer(bad_dur):
    """15/30/60 dışındaki yeni değerler serializer'da reddedilir."""
    from apps.campaigns.serializers import PharmacyCampaignSerializer
    data = {
        "name": f"bad_{bad_dur}",
        "media_url": "https://files.eisa.com.tr/eisa-files/ads/test.jpg",
        "start_at": timezone.now().isoformat(),
        "end_at": (timezone.now() + _dt.timedelta(days=10)).isoformat(),
        "duration_seconds": bad_dur,
        "target_pharmacies": [],
        "target_iller": [],
        "target_ilceler": [],
    }
    s = PharmacyCampaignSerializer(data=data)
    s.is_valid()
    assert "duration_seconds" in s.errors, f"dur={bad_dur} reddedilmedi: {s.errors}"


# ─── PC-08..11: Hedefleme testleri ───────────────────────────────────────────

@pytest.mark.django_db
def test_pc08_direct_pharmacy_match(eczaci_a, eczane_a):
    """Doğrudan eczane hedefi eşleşir."""
    camp = _make_campaign("Direkt", pharmacies=[eczane_a])
    client = APIClient()
    client.force_authenticate(user=eczaci_a)
    resp = client.get(FEED_URL)
    assert resp.status_code == 200
    assert any(c["id"] == str(camp.id) for c in resp.data)


@pytest.mark.django_db
def test_pc09_il_target_matches(eczaci_a, eczane_a, il):
    """İl hedefi eczanenin ili üzerinden eşleşir."""
    camp = _make_campaign("İl Hedefi", iller=[il])
    client = APIClient()
    client.force_authenticate(user=eczaci_a)
    resp = client.get(FEED_URL)
    assert resp.status_code == 200
    assert any(c["id"] == str(camp.id) for c in resp.data)


@pytest.mark.django_db
def test_pc10_ilce_target_matches(eczaci_a, eczane_a, ilce):
    """İlçe hedefi eczanenin ilçesi üzerinden eşleşir."""
    camp = _make_campaign("İlçe Hedefi", ilceler=[ilce])
    client = APIClient()
    client.force_authenticate(user=eczaci_a)
    resp = client.get(FEED_URL)
    assert resp.status_code == 200
    assert any(c["id"] == str(camp.id) for c in resp.data)


@pytest.mark.django_db
def test_pc11_wrong_targets_excluded(eczaci_a, eczane_b, il_baska, ilce_baska):
    """Başka il/ilçe/eczane hedefi feed'e girmez."""
    _make_campaign("Başka Eczane", pharmacies=[eczane_b])
    _make_campaign("Başka İl", iller=[il_baska])
    _make_campaign("Başka İlçe", ilceler=[ilce_baska])

    client = APIClient()
    client.force_authenticate(user=eczaci_a)
    resp = client.get(FEED_URL)
    assert resp.status_code == 200
    assert resp.data == [], f"Eşleşme beklenmiyordu: {resp.data}"


# ─── PC-12: Distinct ─────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_pc12_multi_condition_distinct(eczaci_a, eczane_a, il, ilce):
    """Hem eczane hem il hem ilçeye hedeflenmiş kampanya feed'de tek kez döner."""
    camp = _make_campaign("Çoklu", pharmacies=[eczane_a], iller=[il], ilceler=[ilce])
    client = APIClient()
    client.force_authenticate(user=eczaci_a)
    resp = client.get(FEED_URL)
    assert resp.status_code == 200
    ids = [c["id"] for c in resp.data]
    assert ids.count(str(camp.id)) == 1, f"Distinct çalışmıyor: {ids}"


# ─── PC-13: Hedefsiz kampanya ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_pc13_no_target_campaign_excluded(eczaci_a):
    """Hiç hedefi olmayan kampanya (M2M'ler boş) feed'e girmez."""
    now = timezone.now()
    c = PharmacyCampaign.objects.create(
        name="Hedefsiz",
        media_url="https://files.eisa.com.tr/eisa-files/ads/test.jpg",
        start_at=now - _dt.timedelta(days=1),
        end_at=now + _dt.timedelta(days=30),
        duration_seconds=15,
        is_active=True,
    )
    assert c.target_pharmacies.count() == 0
    assert c.target_iller.count() == 0
    assert c.target_ilceler.count() == 0

    client = APIClient()
    client.force_authenticate(user=eczaci_a)
    resp = client.get(FEED_URL)
    assert resp.status_code == 200
    assert not any(x["id"] == str(c.id) for x in resp.data), "Hedefsiz kampanya feed'de görünmemeli"
