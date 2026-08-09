"""2026-08-09 - Issue fix regression tests.

Kapsamlar:
  T-01  active_media_url video URL kabul edilir (backend serializer)
  T-02  Image/image eski akisi bozulmaz
  T-03  GET day-stream endpoint hicbir DB mutation uretmez
  T-04  day-stream dogru kiosk+tarih verisini doner
  T-05  day-stream kiosk offline -> is_online=False
  T-06  day-stream playlist yok -> hours=[] doner
  T-07  Aktivasyon GenerationJob olusturur
  T-08  Job exception sonsuza kadar PENDING kalmaz (RETRY/FAILED'a gecer)
  T-09  drain_queue islenen job'u DONE/FAILED'a ceker
  T-10  Creative/HouseAd ayrimi KioskPlaylistItemSerializer'da dogru
"""
from __future__ import annotations

import datetime as _dt
import zoneinfo

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    Creative,
    GenerationJob,
    HouseAd,
    Playlist,
    PlaylistItem,
)
from apps.campaigns.serializers import CreativeSerializer
from apps.campaigns.services.invalidation_service import _create_or_coalesce_job
from apps.campaigns.services.queue_worker import (
    _handle_failure,
    claim_next_job,
    drain_queue,
)
from apps.pharmacies.models import Kiosk

_TZ = zoneinfo.ZoneInfo("Europe/Istanbul")
TODAY = _dt.datetime.now(_TZ).date()


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_kiosk2(eczane, mac, online=True):
    return Kiosk.objects.create(
        eczane=eczane,
        ad="IssueTestKiosk",
        mac_adresi=mac,
        aktif=True,
        is_online=online,
    )


def _make_campaign(target_scope="ALL", start_offset=-1, end_offset=5, name="IssueTestCamp"):
    base = timezone.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))
    return Campaign.objects.create(
        name=name,
        start_date=base + _dt.timedelta(days=start_offset),
        end_date=base + _dt.timedelta(days=end_offset),
        status=Campaign.Status.ACTIVE,
        target_scope=target_scope,
    )


def _make_playlist(kiosk, target_date, target_hour=10, version=1):
    return Playlist.objects.create(
        kiosk=kiosk,
        target_date=target_date,
        target_hour=target_hour,
        version=version,
        loop_duration_seconds=60,
    )


# ── T-01: active_media_url video URL kabul edilir ────────────────────────────


@pytest.mark.django_db
def test_t01_active_media_url_accepts_video():
    campaign = _make_campaign()
    data = {
        "campaign": str(campaign.id),
        "media_url": "https://files.eisa.com.tr/eisa-files/ads/idle.jpg",
        "active_media_url": "https://files.eisa.com.tr/eisa-files/ads/active.mp4",
        "duration_seconds": 15,
        "name": "VideoActiveTest",
    }
    s = CreativeSerializer(data=data)
    assert s.is_valid(), s.errors
    creative = s.save()
    assert "mp4" in creative.active_media_url


@pytest.mark.django_db
def test_t01b_active_media_url_accepts_webm():
    campaign = _make_campaign(name="T01b")
    data = {
        "campaign": str(campaign.id),
        "media_url": "https://files.eisa.com.tr/eisa-files/ads/idle.jpg",
        "active_media_url": "https://files.eisa.com.tr/eisa-files/ads/active.webm",
        "duration_seconds": 15,
        "name": "WebmActiveTest",
    }
    s = CreativeSerializer(data=data)
    assert s.is_valid(), s.errors


# ── T-02: Image/image eski akis bozulmaz ─────────────────────────────────────


@pytest.mark.django_db
def test_t02_image_image_legacy_flow_intact():
    campaign = _make_campaign(name="T02")
    data = {
        "campaign": str(campaign.id),
        "media_url": "https://files.eisa.com.tr/eisa-files/ads/idle.jpg",
        "active_media_url": "https://files.eisa.com.tr/eisa-files/ads/active.png",
        "duration_seconds": 15,
        "name": "ImageImageTest",
    }
    s = CreativeSerializer(data=data)
    assert s.is_valid(), s.errors


@pytest.mark.django_db
def test_t02b_empty_active_media_url_allowed():
    campaign = _make_campaign(name="T02b")
    data = {
        "campaign": str(campaign.id),
        "media_url": "https://files.eisa.com.tr/eisa-files/ads/idle.jpg",
        "active_media_url": "",
        "duration_seconds": 15,
        "name": "EmptyActiveTest",
    }
    s = CreativeSerializer(data=data)
    assert s.is_valid(), s.errors


# ── T-03: GET day-stream hicbir DB mutation uretmez ──────────────────────────


@pytest.mark.django_db
def test_t03_day_stream_no_db_mutation(kiosk, admin_client):
    before_jobs = GenerationJob.objects.count()
    before_playlists = Playlist.objects.count()

    resp = admin_client.get(
        "/api/campaigns/v2/playlists/day-stream/",
        {"kiosk": kiosk.id, "date": str(TODAY)},
    )

    assert resp.status_code == 200
    assert GenerationJob.objects.count() == before_jobs, "GET day-stream GenerationJob olusturmamal"
    assert Playlist.objects.count() == before_playlists, "GET day-stream Playlist olusturmamal"


# ── T-04: day-stream dogru veriyi doner ──────────────────────────────────────


@pytest.mark.django_db
def test_t04_day_stream_returns_correct_data(kiosk, admin_client):
    campaign = _make_campaign()
    creative = Creative.objects.create(
        campaign=campaign,
        media_url="https://files.eisa.com.tr/eisa-files/ads/idle.jpg",
        active_media_url="https://files.eisa.com.tr/eisa-files/ads/active.mp4",
        duration_seconds=15,
    )
    pl = _make_playlist(kiosk, TODAY, target_hour=10)
    PlaylistItem.objects.create(
        playlist=pl,
        creative=creative,
        playback_order=1,
        estimated_start_offset_seconds=0,
    )

    resp = admin_client.get(
        "/api/campaigns/v2/playlists/day-stream/",
        {"kiosk": kiosk.id, "date": str(TODAY)},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["kiosk_id"] == kiosk.id
    assert len(data["hours"]) == 1
    assert data["hours"][0]["target_hour"] == 10
    item = data["hours"][0]["items"][0]
    assert item["asset_type"] == "creative"
    assert "idle.jpg" in item["media_url"]
    assert "active.mp4" in item["active_media_url"]


# ── T-05: day-stream kiosk offline -> is_online=False ────────────────────────


@pytest.mark.django_db
def test_t05_day_stream_kiosk_offline(eczane, admin_client):
    kiosk2 = _make_kiosk2(eczane, mac="BC:CD:DE:EF:F0:01", online=False)
    Kiosk.objects.filter(pk=kiosk2.pk).update(is_online=False)
    resp = admin_client.get(
        "/api/campaigns/v2/playlists/day-stream/",
        {"kiosk": kiosk2.id, "date": str(TODAY)},
    )
    assert resp.status_code == 200
    assert resp.json()["is_online"] is False


# ── T-06: day-stream playlist yok -> hours=[] ────────────────────────────────


@pytest.mark.django_db
def test_t06_day_stream_no_playlist(kiosk, admin_client):
    resp = admin_client.get(
        "/api/campaigns/v2/playlists/day-stream/",
        {"kiosk": kiosk.id, "date": str(TODAY)},
    )
    assert resp.status_code == 200
    assert resp.json()["hours"] == []


# ── T-06b: day-stream kiosk parametresi zorunlu -> 400 ───────────────────────


@pytest.mark.django_db
def test_t06b_day_stream_requires_kiosk(admin_client):
    resp = admin_client.get("/api/campaigns/v2/playlists/day-stream/", {"date": str(TODAY)})
    assert resp.status_code == 400


# ── T-06c: day-stream canonical desired/applied alanlari doner ───────────────


@pytest.mark.django_db
def test_t06c_day_stream_desired_applied_canonical(kiosk, admin_client):
    """desired_version = last_playlist_version; applied_version = applied_playlist_version."""
    Kiosk.objects.filter(pk=kiosk.pk).update(
        last_playlist_version=6, applied_playlist_version=None, is_online=True,
    )
    resp = admin_client.get(
        "/api/campaigns/v2/playlists/day-stream/",
        {"kiosk": kiosk.id, "date": str(TODAY)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["desired_version"] == 6
    assert data["applied_version"] is None  # kiosk henuz ACK gondermedi


# ── T-06d: day-stream N+1 yok — sabit sorgu butcesi ──────────────────────────


@pytest.mark.django_db
def test_t06d_day_stream_no_n_plus_1(kiosk, admin_client, django_assert_max_num_queries):
    """Cok sayida playlist item olsa bile sorgu sayisi sabit kalmali (N+1 yok)."""
    campaign = _make_campaign(name="T06d")
    for i in range(6):
        cr = Creative.objects.create(
            campaign=campaign,
            media_url=f"https://files.eisa.com.tr/eisa-files/ads/t06d-{i}.jpg",
            duration_seconds=15,
        )
        for hour in range(3):
            pl, _ = Playlist.objects.get_or_create(
                kiosk=kiosk, target_date=TODAY, target_hour=hour,
                defaults={"version": 1, "loop_duration_seconds": 60},
            )
            PlaylistItem.objects.create(
                playlist=pl, creative=cr,
                playback_order=i + 1, estimated_start_offset_seconds=i * 15,
            )
    # Kiosk + playlists + prefetch(items, creative, campaign, house_ad) → sabit sorgu
    with django_assert_max_num_queries(12):
        resp = admin_client.get(
            "/api/campaigns/v2/playlists/day-stream/",
            {"kiosk": kiosk.id, "date": str(TODAY)},
        )
    assert resp.status_code == 200


# ── T-06e: estimated_start_offset_seconds saat-mutlak 0..3599 ────────────────


@pytest.mark.django_db
def test_t06e_day_stream_offset_hour_absolute(kiosk, admin_client):
    campaign = _make_campaign(name="T06e")
    creative = Creative.objects.create(
        campaign=campaign,
        media_url="https://files.eisa.com.tr/eisa-files/ads/t06e.jpg",
        duration_seconds=15,
    )
    pl = _make_playlist(kiosk, TODAY, target_hour=14)
    PlaylistItem.objects.create(
        playlist=pl, creative=creative,
        playback_order=1, estimated_start_offset_seconds=3599,
    )
    resp = admin_client.get(
        "/api/campaigns/v2/playlists/day-stream/",
        {"kiosk": kiosk.id, "date": str(TODAY)},
    )
    assert resp.status_code == 200
    item = resp.json()["hours"][0]["items"][0]
    assert 0 <= item["estimated_start_offset_seconds"] <= 3599


# ── T-07: Aktivasyon GenerationJob olusturur ─────────────────────────────────


@pytest.mark.django_db
def test_t07_manual_generate_creates_pending_job(kiosk, admin_client):
    before = GenerationJob.objects.count()
    resp = admin_client.post(
        "/api/campaigns/v2/playlists/generate/",
        {"kiosk_ids": [kiosk.id], "scope": "kiosks", "date": str(TODAY)},
        format="json",
    )
    assert resp.status_code == 202
    assert GenerationJob.objects.count() > before
    assert GenerationJob.objects.filter(kiosk=kiosk, status="PENDING").exists()


# ── T-08: Job exception -> RETRY/FAILED, PENDING kalmaz ─────────────────────


@pytest.mark.django_db
def test_t08_job_failure_transitions_to_retry_or_failed(kiosk):
    job = _create_or_coalesce_job(kiosk.id, TODAY, "test_t08")
    assert job.status == "PENDING"

    claimed = claim_next_job()
    assert claimed is not None

    _handle_failure(claimed, RuntimeError("Test failure T08"))

    claimed.refresh_from_db()
    assert claimed.status in ("RETRY", "FAILED")
    assert claimed.status != "PENDING"


# ── T-09: drain_queue islenen job'u terminal duruma gecirir ──────────────────


@pytest.mark.django_db
def test_t09_drain_queue_processes_job(kiosk):
    """drain_queue PENDING job'i claim ederek terminal duruma (DONE/FAILED) gecirir."""
    # HouseAd fillerler icin en az bir house_ad lazim (scheduler bozu calismasin diye)
    HouseAd.objects.create(
        name="T09 Filler",
        media_url="https://files.eisa.com.tr/eisa-files/ads/filler.jpg",
        duration_seconds=15,
        aktif=True,
    )
    job = _create_or_coalesce_job(kiosk.id, TODAY, "test_t09")
    assert job.status == "PENDING"

    with override_settings(DOOH_HORIZON_DAYS=1):
        drain_queue(max_jobs=1)

    job.refresh_from_db()
    assert job.status in ("DONE", "FAILED")
    assert job.status not in ("PENDING", "RUNNING")


# ── T-10: Creative/HouseAd ayrimi KioskPlaylistItemSerializer'da dogru ───────


@pytest.mark.django_db
def test_t10_playlist_item_serializer_creative_vs_house_ad(kiosk):
    from apps.campaigns.serializers import KioskPlaylistItemSerializer

    campaign = _make_campaign(name="T10")
    creative = Creative.objects.create(
        campaign=campaign,
        media_url="https://files.eisa.com.tr/eisa-files/ads/creative.jpg",
        active_media_url="",
        duration_seconds=15,
    )
    ha = HouseAd.objects.create(
        name="T10 HouseAd",
        media_url="https://files.eisa.com.tr/eisa-files/ads/housead.jpg",
        duration_seconds=10,
        aktif=True,
    )
    pl = _make_playlist(kiosk, TODAY, target_hour=9)
    creative_item = PlaylistItem.objects.create(
        playlist=pl, creative=creative,
        playback_order=1, estimated_start_offset_seconds=0,
    )
    ha_item = PlaylistItem.objects.create(
        playlist=pl, house_ad=ha,
        playback_order=2, estimated_start_offset_seconds=15,
    )

    cr_data = KioskPlaylistItemSerializer(creative_item).data
    ha_data = KioskPlaylistItemSerializer(ha_item).data

    assert cr_data["asset_type"] == "creative"
    assert ha_data["asset_type"] == "house_ad"
    assert cr_data["active_media_url"] == ""
    assert ha_data["active_media_url"] == ""
