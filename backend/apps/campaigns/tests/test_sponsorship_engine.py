"""Sponsorship engine testleri — saf cekirdek + uygulanabilirlik + persist.

Yerlesim algoritmasinin homojenligi, saat siniri, round-robin, staggering,
determinizm, pencere kenarlari, kapasite ustu ve karisik sureler.
"""
from __future__ import annotations

import datetime as _dt

import pytest
from django.utils import timezone

from apps.campaigns.models import Campaign, Creative, KioskSponsorship, Playlist
from apps.campaigns.services import sponsorship_engine as engine
from apps.campaigns.services.sponsorship_engine import (
    CreativeSpec,
    Spec,
    plan_day,
    regenerate_kiosk_day,
)

TODAY = _dt.date(2026, 7, 21)  # Sali (ISO weekday=2)


def _spec(key, count, ws_min, we_min, durations=(15,), campaign_id=None):
    creatives = tuple(
        CreativeSpec(id=f"{key}-c{i}", duration=d) for i, d in enumerate(durations)
    )
    return Spec(
        key=key,
        campaign_id=campaign_id or key,
        campaign_name=key,
        window_start_minute=ws_min,
        window_end_minute=we_min,
        count=count,
        creatives=creatives,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Saf cekirdek — yerlesim ozellikleri
# ─────────────────────────────────────────────────────────────────────────────

def test_homogeneous_spacing_spreads_across_all_hours():
    """08:00-19:00 N=100 → 11 saatin tamamina yayilmali, kümelenmemeli."""
    spec = _spec("s1", count=100, ws_min=480, we_min=1140)  # 08:00-19:00
    plan = plan_day(TODAY, [spec])

    assert plan.ok
    assert len(plan.items) == 100
    hours_used = {it.hour for it in plan.items}
    # 08..18 arasi 11 saatin hepsinde en az bir gosterim olmali.
    assert hours_used == set(range(8, 19)), hours_used

    # Ardisik gosterimler arasi bosluk ~ (E-S)/N = 396sn.
    starts = sorted(it.start_second for it in plan.items)
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    avg_gap = sum(gaps) / len(gaps)
    assert 300 <= avg_gap <= 500, avg_gap


def test_offsets_within_hour_and_no_boundary_crossing():
    """Tum offsetler 0..3599 ve hicbir item saat sinirini asmamali."""
    spec = _spec("s1", count=200, ws_min=0, we_min=1440, durations=(30,))
    plan = plan_day(TODAY, [spec])
    for it in plan.items:
        assert 0 <= it.offset <= 3599
        assert it.offset + it.duration <= 3600, (it.offset, it.duration)
        assert it.hour == it.start_second // 3600


def test_no_overlaps():
    """Ayni kiosk-gun icinde hicbir item cakismamali."""
    specs = [
        _spec("a", count=150, ws_min=480, we_min=1140, durations=(15,)),
        _spec("b", count=120, ws_min=480, we_min=1140, durations=(30,)),
    ]
    plan = plan_day(TODAY, specs)
    intervals = sorted((it.start_second, it.start_second + it.duration) for it in plan.items)
    for (s1, e1), (s2, e2) in zip(intervals, intervals[1:]):
        assert e1 <= s2, f"overlap: {(s1, e1)} vs {(s2, e2)}"


def test_creative_round_robin_rotation():
    """Creative'ler yaratim sirasina gore round-robin donmeli."""
    spec = _spec("s1", count=9, ws_min=480, we_min=1140,
                 durations=(15, 15, 15))  # 3 creative
    plan = plan_day(TODAY, [spec])
    # Yerlesim ideal zamana gore siralandigindan start_second'a gore sirala.
    ordered = sorted(plan.items, key=lambda it: it.start_second)
    creative_ids = [it.creative_id for it in ordered]
    # 3 ayri creative, her biri 3 kez.
    from collections import Counter
    counts = Counter(creative_ids)
    assert len(counts) == 3
    assert all(v == 3 for v in counts.values()), counts


def test_staggering_of_two_sponsorships():
    """Iki sponsorluk ayni pencerede faz kaymasi ile serpistirilmeli."""
    specs = [
        _spec("a", count=50, ws_min=480, we_min=1140, campaign_id="A"),
        _spec("b", count=50, ws_min=480, we_min=1140, campaign_id="B"),
    ]
    plan = plan_day(TODAY, specs)
    a_starts = sorted(it.start_second for it in plan.items if it.key == "a")
    b_starts = sorted(it.start_second for it in plan.items if it.key == "b")
    assert len(a_starts) == 50 and len(b_starts) == 50
    # A ve B gosterimleri birebir ayni saniyede baslamamali (staggering).
    assert not (set(a_starts) & set(b_starts))


def test_determinism_and_fingerprint_stability():
    """Ayni girdi → ayni fingerprint ve ayni yerlesim."""
    spec = _spec("s1", count=80, ws_min=480, we_min=1140)
    p1 = plan_day(TODAY, [spec])
    p2 = plan_day(TODAY, [spec])
    assert p1.fingerprint == p2.fingerprint
    assert [(it.start_second, it.creative_id) for it in p1.items] == \
           [(it.start_second, it.creative_id) for it in p2.items]


def test_window_edges_full_day_and_short_window():
    """00:00-24:00 ve cok kisa pencere dogru calismali."""
    full = plan_day(TODAY, [_spec("full", count=500, ws_min=0, we_min=1440)])
    assert full.ok and len(full.items) == 500
    assert min(it.start_second for it in full.items) >= 0
    assert max(it.start_second + it.duration for it in full.items) <= 86400

    short = plan_day(TODAY, [_spec("short", count=3, ws_min=600, we_min=610)])  # 10:00-10:10
    assert len(short.items) == 3
    for it in short.items:
        assert 36000 <= it.start_second < 36600


def test_unplaced_when_over_capacity():
    """Kapasite asilinca fazla gosterimler unplaced olmali."""
    # 10:00-10:05 (300sn), 60sn'lik gosterim → saatte en fazla 5 sigar.
    spec = _spec("s1", count=50, ws_min=600, we_min=605, durations=(60,))
    plan = plan_day(TODAY, [spec])
    st = plan.assignment_stats["s1"]
    assert st.requested == 50
    assert st.placed < 50
    assert st.unplaced == st.requested - st.placed
    assert not plan.ok


def test_mixed_durations_15_30_45_60():
    """Karisik sureli creative'ler saat sinirina uymali."""
    spec = _spec("mix", count=40, ws_min=480, we_min=1140,
                 durations=(15, 30, 45, 60))
    plan = plan_day(TODAY, [spec])
    for it in plan.items:
        assert it.duration in (15, 30, 45, 60)
        assert it.offset + it.duration <= 3600


# ─────────────────────────────────────────────────────────────────────────────
# Uygulanabilirlik (DB wrapper)
# ─────────────────────────────────────────────────────────────────────────────

def _mk_campaign(name="C", status=Campaign.Status.ACTIVE, days=(-1, 30)):
    now = timezone.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))
    camp = Campaign.objects.create(
        name=name,
        start_date=now + _dt.timedelta(days=days[0]),
        end_date=now + _dt.timedelta(days=days[1]),
        status=status,
    )
    return camp


def _mk_creative(camp, duration=15):
    return Creative.objects.create(
        campaign=camp,
        media_url=f"https://cdn.example.com/{camp.id}-{duration}.mp4",
        duration_seconds=duration,
    )


@pytest.mark.django_db
def test_applicability_weekday_filter(kiosk):
    """active_weekdays TODAY'in gunune uymuyorsa gosterim olmaz."""
    camp = _mk_campaign()
    _mk_creative(camp)
    # TODAY = Sali (ISO 2). Sadece Pazartesi (1) aktif → bos.
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=480,
        window_end_minute=1140, count=10, active_weekdays=[1],
    )
    plan = engine.plan_kiosk_day(kiosk, TODAY)
    assert len(plan.items) == 0

    # Sali (2) aktif → dolu.
    KioskSponsorship.objects.filter(kiosk=kiosk).update(active_weekdays=[2])
    plan2 = engine.plan_kiosk_day(kiosk, TODAY)
    assert len(plan2.items) == 10


@pytest.mark.django_db
def test_applicability_campaign_dates(kiosk):
    """Kampanya tarih araligi disindaki gun bos olmali."""
    camp = _mk_campaign(days=(-30, -10))  # TODAY'den once bitmis
    _mk_creative(camp)
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=480,
        window_end_minute=1140, count=5,
    )
    plan = engine.plan_kiosk_day(kiosk, TODAY)
    assert len(plan.items) == 0


@pytest.mark.django_db
def test_applicability_assignment_dates(kiosk):
    """Atama-seviyesi tarih araligi disinda bos olmali."""
    camp = _mk_campaign()
    _mk_creative(camp)
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=480,
        window_end_minute=1140, count=5,
        start_date=TODAY + _dt.timedelta(days=5),
    )
    plan = engine.plan_kiosk_day(kiosk, TODAY)
    assert len(plan.items) == 0


@pytest.mark.django_db
def test_applicability_inactive_assignment(kiosk):
    camp = _mk_campaign()
    _mk_creative(camp)
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=480,
        window_end_minute=1140, count=5, is_active=False,
    )
    plan = engine.plan_kiosk_day(kiosk, TODAY)
    assert len(plan.items) == 0


@pytest.mark.django_db
def test_applicability_paused_campaign(kiosk):
    camp = _mk_campaign(status=Campaign.Status.PAUSED)
    _mk_creative(camp)
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=480,
        window_end_minute=1140, count=5,
    )
    plan = engine.plan_kiosk_day(kiosk, TODAY)
    assert len(plan.items) == 0


@pytest.mark.django_db
def test_applicability_campaign_without_creatives(kiosk):
    camp = _mk_campaign()  # creative yok
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=480,
        window_end_minute=1140, count=5,
    )
    plan = engine.plan_kiosk_day(kiosk, TODAY)
    assert len(plan.items) == 0


@pytest.mark.django_db
def test_opt_in_new_kiosk_empty_schedule(kiosk):
    """Atamasi olmayan kiosk → bos program, 24 bos playlist."""
    n = regenerate_kiosk_day(kiosk.id, TODAY)
    playlists = Playlist.objects.filter(kiosk=kiosk, target_date=TODAY)
    assert playlists.count() == 24
    assert sum(p.items.count() for p in playlists) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Persist — 24 playlist, versiyon artimi, degismeyince atlama
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_persist_creates_24_playlists(kiosk):
    camp = _mk_campaign()
    _mk_creative(camp)
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=0,
        window_end_minute=1440, count=48,
    )
    regenerate_kiosk_day(kiosk.id, TODAY)
    playlists = Playlist.objects.filter(kiosk=kiosk, target_date=TODAY)
    assert playlists.count() == 24
    total_items = sum(p.items.count() for p in playlists)
    assert total_items == 48
    # Offsetler saat ici (0..3599).
    for p in playlists:
        for it in p.items.all():
            assert 0 <= it.estimated_start_offset_seconds <= 3599


@pytest.mark.django_db
def test_persist_version_bump_even_after_wipe(kiosk):
    """Wipe sonrasi bile versiyon kiosk.last_playlist_version'dan buyuk olmali."""
    camp = _mk_campaign()
    _mk_creative(camp)
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=0,
        window_end_minute=1440, count=10,
    )
    regenerate_kiosk_day(kiosk.id, TODAY)
    kiosk.refresh_from_db()
    v1 = kiosk.last_playlist_version
    assert v1 is not None and v1 >= 1

    # Playlist satirlarini sil (wipe) ama last_playlist_version'i koru.
    Playlist.objects.filter(kiosk=kiosk, target_date=TODAY).delete()
    regenerate_kiosk_day(kiosk.id, TODAY)
    kiosk.refresh_from_db()
    assert kiosk.last_playlist_version > v1


@pytest.mark.django_db
def test_persist_no_bump_when_unchanged(kiosk):
    """Icerik degismediyse versiyon artmamali (None doner)."""
    camp = _mk_campaign()
    _mk_creative(camp)
    KioskSponsorship.objects.create(
        kiosk=kiosk, campaign=camp, window_start_minute=0,
        window_end_minute=1440, count=10,
    )
    regenerate_kiosk_day(kiosk.id, TODAY)
    kiosk.refresh_from_db()
    v1 = kiosk.last_playlist_version

    result = regenerate_kiosk_day(kiosk.id, TODAY)
    kiosk.refresh_from_db()
    assert result is None
    assert kiosk.last_playlist_version == v1
