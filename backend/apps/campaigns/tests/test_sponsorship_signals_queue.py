"""Sinyal, queue worker, kiosk sync ve migration-cleanup testleri."""
from __future__ import annotations

import datetime as _dt

import pytest
from django.apps import apps as django_apps
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    Creative,
    GenerationJob,
    KioskSponsorship,
    PlayLog,
    Playlist,
)
from apps.campaigns.services.invalidation_service import get_horizon_dates
from apps.campaigns.services.queue_worker import drain_queue
from apps.campaigns.services.sponsorship_engine import _horizon_today
from apps.pharmacies.models import Kiosk

TODAY = _horizon_today()


def _mk_campaign(name="C", duration=15, creatives=1):
    now = timezone.now()
    camp = Campaign.objects.create(
        name=name, start_date=now - _dt.timedelta(days=1),
        end_date=now + _dt.timedelta(days=30), status=Campaign.Status.ACTIVE,
    )
    for i in range(creatives):
        Creative.objects.create(
            campaign=camp, media_url=f"https://cdn.example.com/{camp.id}-{i}.mp4",
            duration_seconds=duration,
        )
    return camp


@pytest.fixture
def kiosk2(db, eczane):
    return Kiosk.objects.create(
        eczane=eczane, ad="Kiosk 2", mac_adresi="AA:BB:CC:DD:EE:22",
        uygulama_anahtari="test-app-key-22-secure-48chars-xxxxxxxxxxxxxxxxx",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sinyaller — sadece atanmis kiosklar icin GenerationJob
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_sponsorship_signal_enqueues_assigned_kiosk_only(
    kiosk, kiosk2, django_capture_on_commit_callbacks
):
    camp = _mk_campaign()
    with django_capture_on_commit_callbacks(execute=True):
        KioskSponsorship.objects.create(
            kiosk=kiosk, campaign=camp, window_start_minute=480,
            window_end_minute=1140, count=10,
        )
    horizon = get_horizon_dates()
    jobs_k1 = GenerationJob.objects.filter(kiosk=kiosk)
    jobs_k2 = GenerationJob.objects.filter(kiosk=kiosk2)
    # kiosk1 atanmis → horizon kadar job; kiosk2 atanmamis → hic job yok.
    assert jobs_k1.count() == len(horizon)
    assert jobs_k2.count() == 0


# ─────────────────────────────────────────────────────────────────────────────
# Queue worker — job'tan playlist uretir
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_queue_worker_produces_playlists(kiosk):
    camp = _mk_campaign()
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=0,
        window_end_minute=1440, count=12,
    )
    GenerationJob.objects.create(
        target_date=TODAY, kiosk=kiosk, status=GenerationJob.JobStatus.PENDING,
        triggered_by="test", dedupe_key=f"kd:{kiosk.id}:{TODAY}",
        payload={"kiosk_id": kiosk.id, "date": str(TODAY), "trigger_reason": "test"},
        available_at=timezone.now(),
    )
    processed = drain_queue(max_jobs=5)
    assert processed >= 1
    playlists = Playlist.objects.filter(kiosk=kiosk, target_date=TODAY)
    assert playlists.count() == 24
    assert sum(p.items.count() for p in playlists) == 12
    job = GenerationJob.objects.get(kiosk=kiosk, target_date=TODAY)
    assert job.status == GenerationJob.JobStatus.DONE


# ─────────────────────────────────────────────────────────────────────────────
# Kiosk sync — yalnizca atanmis creative'ler
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_kiosk_sync_returns_only_assigned_creatives(kiosk_client, kiosk):
    assigned = _mk_campaign(name="Atanmis")
    unassigned = _mk_campaign(name="Atanmamis")
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=assigned, window_start_minute=480,
        window_end_minute=1140, count=5,
    )
    r = kiosk_client.get("/api/kiosk/v1/sync/")
    assert r.status_code == 200, r.content
    returned_campaigns = {
        str(c["campaign"]) if "campaign" in c else None
        for c in r.json()["creatives"]
    }
    assigned_creative_ids = {
        str(x.id) for x in assigned.creatives.all()
    }
    returned_ids = {str(c["id"]) for c in r.json()["creatives"]}
    assert returned_ids == assigned_creative_ids
    # Atanmamis kampanyanin creative'i donmemeli
    unassigned_ids = {str(x.id) for x in unassigned.creatives.all()}
    assert not (returned_ids & unassigned_ids)


# ─────────────────────────────────────────────────────────────────────────────
# Migration cleanup — cleanup_sponsorship_data dogrudan
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_migration_cleanup_function(kiosk):
    import importlib
    _0033 = importlib.import_module(
        "apps.campaigns.migrations.0033_cleanup_sponsorship_data"
    )
    cleanup = _0033.cleanup_sponsorship_data

    camp = _mk_campaign()
    creative = camp.creatives.first()
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=0,
        window_end_minute=1440, count=5,
    )
    # Mevcut playlist + playlog + job
    pl = Playlist.objects.create(kiosk=kiosk, target_date=TODAY, target_hour=0)
    playlog = PlayLog.objects.create(
        kiosk=kiosk, creative=creative,
        status=PlayLog.PlayStatus.COMPLETED,
        played_at=timezone.now(), duration_played=15,
    )
    GenerationJob.objects.create(
        target_date=TODAY, kiosk=kiosk, status=GenerationJob.JobStatus.DONE,
        triggered_by="old",
    )

    cleanup(django_apps, None)

    # Campaign/Creative/Playlist silinmeli
    assert Campaign.objects.count() == 0
    assert Creative.objects.count() == 0
    assert Playlist.objects.count() == 0
    # PlayLog korunur, creative NULL'a cekilir
    playlog.refresh_from_db()
    assert playlog.creative_id is None
    # Aktif kiosk icin PENDING is olusturulmali (yuksek versiyonlu bos program)
    pending = GenerationJob.objects.filter(
        kiosk=kiosk, status="PENDING", triggered_by="data_cleanup"
    )
    assert pending.count() == len(get_horizon_dates())
