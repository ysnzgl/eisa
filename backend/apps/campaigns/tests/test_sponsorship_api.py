"""Sponsorship yonetim API testleri (DRF, SuperAdmin).

Auth, kiosk listesi, PUT replace, kapasite bloklama, preview, copy, assign,
simulate ve blokaj senaryolarini kapsar.
"""
from __future__ import annotations

import datetime as _dt

import pytest
from django.utils import timezone

from apps.campaigns.models import Campaign, Creative, KioskSponsorship, Playlist
from apps.campaigns.services.sponsorship_engine import _horizon_today
from apps.pharmacies.models import Eczane, Kiosk

BASE = "/api/campaigns/v2"
TODAY = _horizon_today()  # Istanbul "bugun" — kapasite dogrulama bugunden baslar


# ─────────────────────────────────────────────────────────────────────────────
# Yardimcilar
# ─────────────────────────────────────────────────────────────────────────────

def _mk_campaign(name="C", status=Campaign.Status.ACTIVE, days=(-1, 60), creatives=1,
                 duration=15):
    base = timezone.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))
    camp = Campaign.objects.create(
        name=name,
        start_date=base + _dt.timedelta(days=days[0]),
        end_date=base + _dt.timedelta(days=days[1]),
        status=status,
    )
    for i in range(creatives):
        Creative.objects.create(
            campaign=camp,
            media_url=f"https://cdn.example.com/{camp.id}-{i}.mp4",
            duration_seconds=duration,
        )
    return camp


@pytest.fixture
def kiosk2(db, eczane):
    return Kiosk.objects.create(
        eczane=eczane, ad="Kiosk 2", mac_adresi="AA:BB:CC:DD:EE:02",
        uygulama_anahtari="test-app-key-2-secure-48chars-xxxxxxxxxxxxxxxxxx",
    )


@pytest.fixture
def kiosk3(db, eczane):
    return Kiosk.objects.create(
        eczane=eczane, ad="Kiosk 3", mac_adresi="AA:BB:CC:DD:EE:03",
        uygulama_anahtari="test-app-key-3-secure-48chars-xxxxxxxxxxxxxxxxxx",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_non_superadmin_forbidden(eczaci_client, kiosk):
    r = eczaci_client.get(f"{BASE}/sponsorship-kiosks/")
    assert r.status_code == 403


@pytest.mark.django_db
def test_anonymous_forbidden(api_client, kiosk):
    r = api_client.get(f"{BASE}/sponsorship-kiosks/")
    assert r.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# Kiosk listesi + unassigned filtresi
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_kiosk_list_and_unassigned_filter(admin_client, kiosk, kiosk2):
    camp = _mk_campaign()
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=480,
        window_end_minute=1140, count=10,
    )
    r = admin_client.get(f"{BASE}/sponsorship-kiosks/")
    assert r.status_code == 200
    ids = {row["id"] for row in r.json()}
    assert kiosk.id in ids and kiosk2.id in ids

    r2 = admin_client.get(f"{BASE}/sponsorship-kiosks/?unassigned=1")
    assert r2.status_code == 200
    ids2 = {row["id"] for row in r2.json()}
    assert kiosk2.id in ids2
    assert kiosk.id not in ids2


# ─────────────────────────────────────────────────────────────────────────────
# PUT replace + duplicate + capacity_exceeded
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_put_replace_sponsorships(admin_client, kiosk):
    camp = _mk_campaign()
    body = {"items": [{
        "campaign_id": str(camp.id),
        "window_start": "08:00", "window_end": "19:00",
        "count": 10, "active_weekdays": None,
        "start_date": None, "end_date": None, "is_active": True,
    }]}
    r = admin_client.put(
        f"{BASE}/sponsorship-kiosks/{kiosk.id}/sponsorships/", body, format="json"
    )
    assert r.status_code == 200, r.content
    assert len(r.json()["items"]) == 1
    assert KioskSponsorship.objects.filter(kiosk=kiosk).count() == 1


@pytest.mark.django_db
def test_put_duplicate_campaign_400(admin_client, kiosk):
    camp = _mk_campaign()
    item = {
        "campaign_id": str(camp.id), "window_start": "08:00",
        "window_end": "19:00", "count": 10,
    }
    body = {"items": [item, dict(item)]}
    r = admin_client.put(
        f"{BASE}/sponsorship-kiosks/{kiosk.id}/sponsorships/", body, format="json"
    )
    assert r.status_code == 400
    assert KioskSponsorship.objects.filter(kiosk=kiosk).count() == 0


@pytest.mark.django_db
def test_put_capacity_exceeded_nothing_saved(admin_client, kiosk):
    # 10:00-10:05 (300sn) icinde 60sn'lik 100 gosterim imkansiz.
    camp = _mk_campaign(duration=60)
    body = {"items": [{
        "campaign_id": str(camp.id), "window_start": "10:00",
        "window_end": "10:05", "count": 100,
    }]}
    r = admin_client.put(
        f"{BASE}/sponsorship-kiosks/{kiosk.id}/sponsorships/", body, format="json"
    )
    assert r.status_code == 400
    assert r.json()["code"] == "capacity_exceeded"
    assert "conflicts" in r.json()
    assert KioskSponsorship.objects.filter(kiosk=kiosk).count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# Preview — DB yazmaz, HH:MM:SS alanlari
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_preview_with_draft_items_no_db_writes(admin_client, kiosk):
    camp = _mk_campaign()
    body = {
        "date": str(TODAY),
        "items": [{
            "campaign_id": str(camp.id), "window_start": "08:00",
            "window_end": "19:00", "count": 20,
        }],
    }
    r = admin_client.post(
        f"{BASE}/sponsorship-kiosks/{kiosk.id}/preview/", body, format="json"
    )
    assert r.status_code == 200, r.content
    data = r.json()
    assert data["ok"] is True
    assert len(data["items"]) == 20
    assert len(data["hours"]) == 24
    # HH:MM:SS alanlari
    first = data["items"][0]
    assert len(first["start"].split(":")) == 3
    assert len(first["end"].split(":")) == 3
    # DB'ye yazilmamali
    assert KioskSponsorship.objects.filter(kiosk=kiosk).count() == 0
    assert Playlist.objects.filter(kiosk=kiosk, target_date=TODAY).count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# Copy — overwrite + dry_run + source-in-targets
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_copy_overwrite(admin_client, kiosk, kiosk2):
    camp = _mk_campaign()
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=480,
        window_end_minute=1140, count=10,
    )
    # kiosk2'de farkli bir kampanya var; overwrite ile silinmeli.
    other = _mk_campaign(name="Other")
    KioskSponsorship.objects.create(
        kiosk=kiosk2, campaign=other, window_start_minute=0,
        window_end_minute=600, count=5,
    )
    r = admin_client.post(
        f"{BASE}/sponsorship-kiosks/{kiosk.id}/copy/",
        {"target_kiosk_ids": [kiosk2.id], "dry_run": False}, format="json",
    )
    assert r.status_code == 200, r.content
    camp_ids = set(
        KioskSponsorship.objects.filter(kiosk=kiosk2).values_list("campaign_id", flat=True)
    )
    assert camp_ids == {camp.id}


@pytest.mark.django_db
def test_copy_dry_run_no_writes(admin_client, kiosk, kiosk2):
    camp = _mk_campaign()
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=480,
        window_end_minute=1140, count=10,
    )
    r = admin_client.post(
        f"{BASE}/sponsorship-kiosks/{kiosk.id}/copy/",
        {"target_kiosk_ids": [kiosk2.id], "dry_run": True}, format="json",
    )
    assert r.status_code == 200
    assert r.json()["dry_run"] is True
    assert KioskSponsorship.objects.filter(kiosk=kiosk2).count() == 0


@pytest.mark.django_db
def test_copy_source_in_targets_400(admin_client, kiosk, kiosk2):
    r = admin_client.post(
        f"{BASE}/sponsorship-kiosks/{kiosk.id}/copy/",
        {"target_kiosk_ids": [kiosk.id, kiosk2.id]}, format="json",
    )
    assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# assign-kiosks — skip-already-assigned + atomic rejection
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_assign_kiosks_skip_already_assigned(admin_client, kiosk, kiosk2):
    camp = _mk_campaign()
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=480,
        window_end_minute=1140, count=10,
    )
    r = admin_client.post(
        f"{BASE}/campaigns/{camp.id}/assign-kiosks/",
        {
            "kiosk_ids": [kiosk.id, kiosk2.id],
            "window_start": "08:00", "window_end": "19:00", "count": 10,
        },
        format="json",
    )
    assert r.status_code == 200, r.content
    data = r.json()
    assert kiosk.id in data["skipped_already_assigned"]
    assert kiosk2.id in data["assigned"]
    assert KioskSponsorship.objects.filter(campaign=camp, kiosk=kiosk2).count() == 1


@pytest.mark.django_db
def test_assign_kiosks_atomic_rejection(admin_client, kiosk, kiosk2):
    # kiosk2 ustunde kapasiteyi dolduran mevcut atama.
    big = _mk_campaign(name="Big", duration=60)
    KioskSponsorship.objects.create(
        kiosk=kiosk2, campaign=big, window_start_minute=600,
        window_end_minute=605, count=5,  # 10:00-10:05 dolu
    )
    camp = _mk_campaign(name="New", duration=60)
    r = admin_client.post(
        f"{BASE}/campaigns/{camp.id}/assign-kiosks/",
        {
            "kiosk_ids": [kiosk.id, kiosk2.id],
            "window_start": "10:00", "window_end": "10:05", "count": 100,
        },
        format="json",
    )
    assert r.status_code == 400
    assert r.json()["code"] == "capacity_exceeded"
    # Hicbir sey kaydedilmemeli (atomic)
    assert KioskSponsorship.objects.filter(campaign=camp).count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# Simulate — probe + scenario
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_simulate_probe_empty_kiosk(admin_client, kiosk):
    """Bos kiosk 08:00-19:00 15sn → en fazla 2640 gosterim."""
    r = admin_client.post(
        f"{BASE}/sponsorship-kiosks/{kiosk.id}/simulate/",
        {
            "date_from": str(TODAY), "date_to": str(TODAY),
            "include_existing": True,
            "probe": {
                "duration_seconds": 15, "window_start": "08:00",
                "window_end": "19:00", "active_weekdays": None,
            },
        },
        format="json",
    )
    assert r.status_code == 200, r.content
    probe = r.json()["probe"]
    assert probe["max_shows_max"] == 2640
    assert probe["max_shows_min"] == 2640


@pytest.mark.django_db
def test_simulate_scenario_feasible_and_infeasible(admin_client, kiosk):
    # Feasible: 10 gosterim 08:00-19:00 15sn.
    r = admin_client.post(
        f"{BASE}/sponsorship-kiosks/{kiosk.id}/simulate/",
        {
            "date_from": str(TODAY), "date_to": str(TODAY),
            "scenario": [{
                "label": "L1", "duration_seconds": 15, "count": 10,
                "window_start": "08:00", "window_end": "19:00",
            }],
        },
        format="json",
    )
    assert r.status_code == 200, r.content
    assert r.json()["scenario"]["feasible"] is True

    # Infeasible: 10:00-10:05 60sn 100 gosterim.
    r2 = admin_client.post(
        f"{BASE}/sponsorship-kiosks/{kiosk.id}/simulate/",
        {
            "date_from": str(TODAY), "date_to": str(TODAY),
            "scenario": [{
                "label": "L2", "duration_seconds": 60, "count": 100,
                "window_start": "10:00", "window_end": "10:05",
            }],
        },
        format="json",
    )
    assert r2.status_code == 200
    assert r2.json()["scenario"]["feasible"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Campaign/Creative update kapasite blokaji
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_campaign_update_blocked_by_capacity(admin_client, kiosk):
    # 10:00-10:05 (300sn), 15sn → saatte 20 sigar. count=20 feasible.
    camp = _mk_campaign(name="C", duration=15, creatives=1)
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=600,
        window_end_minute=605, count=20,
    )
    # Creative suresini 60'a cikaran update kapasiteyi bozdugu icin bloklanmali.
    creative = camp.creatives.first()
    r = admin_client.patch(
        f"{BASE}/creatives/{creative.id}/",
        {"duration_seconds": 60}, format="json",
    )
    assert r.status_code == 400, r.content
    assert r.json()["code"] == "capacity_exceeded"
    creative.refresh_from_db()
    assert creative.duration_seconds == 15


@pytest.mark.django_db
def test_creative_create_blocked_by_capacity(admin_client, kiosk):
    camp = _mk_campaign(name="C", duration=15, creatives=1)
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=600,
        window_end_minute=605, count=20,
    )
    # Yeni 60sn'lik creative round-robin'e girince kapasite asilir.
    r = admin_client.post(
        f"{BASE}/creatives/",
        {
            "campaign": str(camp.id),
            "media_url": "https://cdn.example.com/new-60.mp4",
            "duration_seconds": 60,
        },
        format="json",
    )
    assert r.status_code == 400
    assert r.json()["code"] == "capacity_exceeded"
    assert camp.creatives.count() == 1
