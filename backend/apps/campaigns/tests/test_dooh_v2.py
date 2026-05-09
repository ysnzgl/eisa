"""DOOH v2 — scheduler ve API endpoint testleri."""
from __future__ import annotations

import datetime as _dt
import uuid

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    Creative,
    HouseAd,
    PlayLog,
    Playlist,
    PlaylistItem,
    ScheduleRule,
)
from apps.campaigns.services.scheduler import (
    PlaylistGenerator,
    available_seconds,
    generate_for_kiosk,
)


# ─── Fixture'lar ─────────────────────────────────────────────────────────────


@pytest.fixture
def active_campaign(db):
    now = timezone.now()
    return Campaign.objects.create(
        advertiser_id=uuid.uuid4(),
        name="Test Campaign",
        start_date=now - _dt.timedelta(days=1),
        end_date=now + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )


@pytest.fixture
def creative_15s(db, active_campaign):
    return Creative.objects.create(
        campaign=active_campaign,
        media_url="https://cdn.example.com/ad15.mp4",
        duration_seconds=15,
        name="15s creative",
    )


@pytest.fixture
def creative_5s(db, active_campaign):
    return Creative.objects.create(
        campaign=active_campaign,
        media_url="https://cdn.example.com/ad5.mp4",
        duration_seconds=5,
    )


@pytest.fixture
def house_ad_10s(db):
    return HouseAd.objects.create(
        name="Health Tip",
        media_url="https://cdn.example.com/health.mp4",
        duration_seconds=10,
    )


# ─── Scheduler core algoritma ────────────────────────────────────────────────


@pytest.mark.django_db
def test_per_loop_distributes_evenly(kiosk, active_campaign, creative_15s):
    """PER_LOOP / freq=2 / dur=15 → 60s loop'ta 0s ve 30s offset'lere yerlesmeli."""
    ScheduleRule.objects.create(
        campaign=active_campaign,
        frequency_type=ScheduleRule.FrequencyType.PER_LOOP,
        frequency_value=2,
    )
    target_date = timezone.now().date()
    playlists = generate_for_kiosk(kiosk, target_date)
    assert len(playlists) == 24
    pl = next(p for p in playlists if p.target_hour == 0)
    # Sadece ilk loop'taki creative slotlarini al (offset < 60)
    first_loop_creatives = [
        i for i in pl.items.all()
        if i.creative_id and i.estimated_start_offset_seconds < pl.loop_duration_seconds
    ]
    assert len(first_loop_creatives) == 2
    offsets = sorted(int(i.estimated_start_offset_seconds) for i in first_loop_creatives)
    assert offsets == [0, 30]


@pytest.mark.django_db
def test_per_loop_capacity_exceeded_skipped(kiosk, active_campaign):
    """duration*frequency > T_loop ise kural skip edilmeli (atilmamali)."""
    Creative.objects.create(
        campaign=active_campaign,
        media_url="https://cdn.example.com/big.mp4",
        duration_seconds=30,
    )
    ScheduleRule.objects.create(
        campaign=active_campaign,
        frequency_type=ScheduleRule.FrequencyType.PER_LOOP,
        frequency_value=3,  # 30 * 3 = 90 > 60
    )
    target_date = timezone.now().date()
    playlists = generate_for_kiosk(kiosk, target_date)
    pl = next(p for p in playlists if p.target_hour == 0)
    # Bu kampanyaya ait creative yerlestirilmemeli
    creative_count = sum(1 for i in pl.items.all() if i.creative_id)
    assert creative_count == 0


@pytest.mark.django_db
def test_per_hour_targets_only_listed_hours(kiosk, active_campaign, creative_15s):
    """target_hours=[18] ise sadece 18'inci saatte yerlesmeli."""
    ScheduleRule.objects.create(
        campaign=active_campaign,
        frequency_type=ScheduleRule.FrequencyType.PER_HOUR,
        frequency_value=1,
        target_hours=[18],
    )
    target_date = timezone.now().date()
    generate_for_kiosk(kiosk, target_date)
    pl_h17 = Playlist.objects.get(kiosk=kiosk, target_date=target_date, target_hour=17)
    pl_h18 = Playlist.objects.get(kiosk=kiosk, target_date=target_date, target_hour=18)

    has_creative_17 = any(i.creative_id == creative_15s.pk for i in pl_h17.items.all())
    has_creative_18 = any(i.creative_id == creative_15s.pk for i in pl_h18.items.all())
    assert has_creative_17 is False
    assert has_creative_18 is True


@pytest.mark.django_db
def test_filler_fills_remaining_seconds(kiosk, house_ad_10s):
    """Kural yoksa Pass 4 house ad ile her loop'u 60sn'e tam doldurmali."""
    target_date = timezone.now().date()
    playlists = generate_for_kiosk(kiosk, target_date)
    pl = next(p for p in playlists if p.target_hour == 0)
    items = list(pl.items.all())
    assert items, "playlist bos olmamali"
    assert all(i.house_ad_id == house_ad_10s.pk for i in items)
    # Her loop 60sn'e dolu olmali
    per_loop: dict[int, int] = {}
    for it in items:
        idx = int(it.estimated_start_offset_seconds) // pl.loop_duration_seconds
        per_loop[idx] = per_loop.get(idx, 0) + int(it.house_ad.duration_seconds)
    assert all(v == 60 for v in per_loop.values())


@pytest.mark.django_db
def test_capacity_invariant_never_exceeded(kiosk, active_campaign, creative_15s, house_ad_10s):
    """Hicbir loop'ta toplam kullanim 60sn'i gecmemeli."""
    ScheduleRule.objects.create(
        campaign=active_campaign,
        frequency_type=ScheduleRule.FrequencyType.PER_LOOP,
        frequency_value=2,
    )
    target_date = timezone.now().date()
    playlists = generate_for_kiosk(kiosk, target_date)
    for pl in playlists:
        per_loop: dict[int, int] = {}
        for item in pl.items.all():
            idx = int(item.estimated_start_offset_seconds) // pl.loop_duration_seconds
            dur = (item.creative.duration_seconds if item.creative_id
                   else item.house_ad.duration_seconds)
            per_loop[idx] = per_loop.get(idx, 0) + int(dur)
        assert per_loop, f"empty playlist h={pl.target_hour}"
        assert max(per_loop.values()) <= pl.loop_duration_seconds


@pytest.mark.django_db
def test_inactive_campaign_skipped(kiosk, creative_15s):
    """Status=PAUSED kampanyalari planlanmamali."""
    creative_15s.campaign.status = Campaign.Status.PAUSED
    creative_15s.campaign.save()
    ScheduleRule.objects.create(
        campaign=creative_15s.campaign,
        frequency_type=ScheduleRule.FrequencyType.PER_LOOP,
        frequency_value=1,
    )
    target_date = timezone.now().date()
    generate_for_kiosk(kiosk, target_date)
    pl = Playlist.objects.get(kiosk=kiosk, target_date=target_date, target_hour=0)
    assert all(i.creative_id is None for i in pl.items.all())


@pytest.mark.django_db
def test_idempotent_regeneration(kiosk, house_ad_10s):
    """Aynı gun icin tekrar uretmek mevcut playlist'leri silip yenisini uretir."""
    target_date = timezone.now().date()
    generate_for_kiosk(kiosk, target_date)
    first = Playlist.objects.filter(kiosk=kiosk, target_date=target_date).count()
    generate_for_kiosk(kiosk, target_date)
    second = Playlist.objects.filter(kiosk=kiosk, target_date=target_date).count()
    assert first == 24 and second == 24


# ─── API endpoint testleri ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_admin_create_campaign_201(admin_client):
    now = timezone.now()
    payload = {
        "advertiser_id": str(uuid.uuid4()),
        "name": "Yeni Kampanya",
        "start_date": now.isoformat(),
        "end_date": (now + _dt.timedelta(days=10)).isoformat(),
        "status": "ACTIVE",
    }
    r = admin_client.post("/api/campaigns/v2/campaigns/", payload, format="json")
    assert r.status_code == 201, r.content
    assert r.json()["name"] == "Yeni Kampanya"


@pytest.mark.django_db
def test_admin_post_rules_for_campaign(admin_client, active_campaign):
    payload = [
        {"frequency_type": "PER_LOOP", "frequency_value": 2},
        {"frequency_type": "PER_HOUR", "frequency_value": 3, "target_hours": [17, 18, 19]},
    ]
    r = admin_client.post(
        f"/api/campaigns/v2/campaigns/{active_campaign.pk}/rules/",
        payload, format="json",
    )
    assert r.status_code == 201, r.content
    data = r.json()
    assert len(data) == 2
    assert ScheduleRule.objects.filter(campaign=active_campaign).count() == 2


@pytest.mark.django_db
def test_inventory_availability_no_playlist_returns_full(admin_client, kiosk):
    target_date = (timezone.now() + _dt.timedelta(days=1)).date()
    r = admin_client.get(
        f"/api/inventory/availability/?date={target_date}&hour=18&kiosk={kiosk.pk}"
    )
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["available_seconds"] == 60
    assert body["hour"] == 18


@pytest.mark.django_db
def test_inventory_availability_after_generation(admin_client, kiosk, active_campaign, creative_15s):
    ScheduleRule.objects.create(
        campaign=active_campaign,
        frequency_type=ScheduleRule.FrequencyType.PER_LOOP,
        frequency_value=2,
    )
    target_date = timezone.now().date()
    generate_for_kiosk(kiosk, target_date)
    # Bir loop'ta 30s creative + 30s filler => available=30 (loop bazinda kalan)
    secs = available_seconds(kiosk, target_date, 18)
    assert secs == 30


@pytest.mark.django_db
def test_kiosk_sync_returns_creatives(kiosk_client, kiosk, active_campaign, creative_15s, house_ad_10s):
    r = kiosk_client.get(f"/api/kiosk/v1/{kiosk.pk}/sync/")
    assert r.status_code == 200, r.content
    body = r.json()
    assert body["kiosk_id"] == kiosk.pk
    creative_ids = {c["id"] for c in body["creatives"]}
    assert str(creative_15s.pk) in creative_ids
    assert len(body["house_ads"]) == 1


@pytest.mark.django_db
def test_kiosk_sync_forbids_other_kiosk(kiosk_client, kiosk, eczane):
    other = type(kiosk).objects.create(
        eczane=eczane,
        mac_adresi="11:22:33:44:55:66",
        uygulama_anahtari="other-key" + "x" * 40,
    )
    r = kiosk_client.get(f"/api/kiosk/v1/{other.pk}/sync/")
    assert r.status_code == 403


@pytest.mark.django_db
def test_kiosk_playlist_endpoint(kiosk_client, kiosk, house_ad_10s):
    target_date = timezone.now().date()
    generate_for_kiosk(kiosk, target_date)
    r = kiosk_client.get(f"/api/kiosk/v1/{kiosk.pk}/playlist/?date={target_date}")
    assert r.status_code == 200, r.content
    body = r.json()
    assert len(body["playlists"]) == 24
    first = body["playlists"][0]
    assert first["loop_duration_seconds"] == 60
    assert len(first["items"]) > 0
    item = first["items"][0]
    assert "media_url" in item and "duration_seconds" in item


@pytest.mark.django_db
def test_kiosk_proof_of_play_bulk_ingest(kiosk_client, kiosk, creative_15s):
    payload = {"logs": [
        {
            "creative_id": str(creative_15s.pk),
            "played_at": timezone.now().isoformat(),
            "duration_played": 15,
        },
        {
            "creative_id": str(creative_15s.pk),
            "played_at": timezone.now().isoformat(),
            "duration_played": 14,
        },
    ]}
    r = kiosk_client.post(
        f"/api/kiosk/v1/{kiosk.pk}/proof-of-play/", payload, format="json",
    )
    assert r.status_code == 201, r.content
    assert r.json()["ingested"] == 2
    assert PlayLog.objects.filter(kiosk=kiosk).count() == 2


@pytest.mark.django_db
def test_kiosk_proof_of_play_validation(kiosk_client, kiosk):
    """Hem creative_id hem house_ad_id eksikse 400."""
    payload = {"logs": [
        {"played_at": timezone.now().isoformat(), "duration_played": 15},
    ]}
    r = kiosk_client.post(
        f"/api/kiosk/v1/{kiosk.pk}/proof-of-play/", payload, format="json",
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_admin_pricing_matrix_create_and_get(admin_client):
    payload = {
        "base_price_per_second": "1.5000",
        "prime_time_coefficient": "2.000",
        "prime_hours": [17, 18, 19, 20],
        "frequency_multipliers": {"PER_LOOP": 3.0, "PER_HOUR": 1.5, "PER_DAY": 1.0},
        "currency": "TRY",
        "is_default": True,
    }
    r = admin_client.put("/api/campaigns/v2/pricing-matrix/", payload, format="json")
    assert r.status_code in (200, 201), r.content

    r2 = admin_client.get("/api/campaigns/v2/pricing-matrix/")
    assert r2.status_code == 200
    body = r2.json()
    assert body["prime_hours"] == [17, 18, 19, 20]
    assert body["currency"] == "TRY"
