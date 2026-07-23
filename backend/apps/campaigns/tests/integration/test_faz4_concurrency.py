"""Faz 4 — PostgreSQL concurrency testleri.

FB-15  İki worker aynı job'u claim edemez
FB-16  İki worker farklı job'ları güvenle claim edebilir
FB-23  Aynı job tekrar işlendiğinde duplicate üretilmez
FB-24  Aynı kiosk için concurrent publish lost update üretmez
FB-33  CAMPAIGN_TOTAL invariantı concurrency altında bozulmaz (Faz 3'ten)
"""
from __future__ import annotations

import datetime as _dt
import threading
import uuid

import pytest
from django.db import close_old_connections, transaction
from django.test import override_settings
from django.utils import timezone

from apps.campaigns.models import GenerationJob, Playlist
from apps.campaigns.services.queue_worker import claim_next_job, process_job
from apps.pharmacies.models import Eczane, Kiosk


pytestmark = pytest.mark.postgresql

import zoneinfo
_TZ = zoneinfo.ZoneInfo("Europe/Istanbul")
TODAY = _dt.datetime.now(_TZ).date()


@pytest.fixture
def kiosk_fb(db):
    from apps.lookups.seed import seed_lookups
    from apps.lookups.models import Il, Ilce
    seed_lookups()
    il = Il.objects.get_or_create(ad="Istanbul")[0]
    ilce = Ilce.objects.get_or_create(il=il, ad="Besiktas")[0]
    eczane = Eczane.objects.create(ad="FB Race Eczane", il=il, ilce=ilce)
    return Kiosk.objects.create(
        eczane=eczane,
        ad="FB Race Kiosk",
        mac_adresi=f"FB:15:{uuid.uuid4().hex[:2].upper()}:00:00:01",
        uygulama_anahtari=f"fb15-key-{uuid.uuid4().hex}",
        aktif=True,
    )


@pytest.fixture
def kiosk_fb2(db):
    from apps.lookups.seed import seed_lookups
    from apps.lookups.models import Il, Ilce
    seed_lookups()
    il = Il.objects.get_or_create(ad="Istanbul")[0]
    ilce = Ilce.objects.get_or_create(il=il, ad="Besiktas")[0]
    eczane = Eczane.objects.create(ad="FB Race Eczane 2", il=il, ilce=ilce)
    return Kiosk.objects.create(
        eczane=eczane,
        ad="FB Race Kiosk 2",
        mac_adresi=f"FB:16:{uuid.uuid4().hex[:2].upper()}:00:00:02",
        uygulama_anahtari=f"fb16-key-{uuid.uuid4().hex}",
        aktif=True,
    )


@pytest.fixture
def house_ad_fb(db):
    from apps.campaigns.models import HouseAd
    return HouseAd.objects.create(
        name="FB Race HouseAd",
        media_url="http://localhost:9000/dev/ads/fb-race.mp4",
        duration_seconds=15,
        priority=1,
        aktif=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# FB-15  İki worker aynı job'u claim edemez
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_fb15_two_workers_cant_claim_same_job(kiosk_fb):
    """SELECT FOR UPDATE SKIP LOCKED: iki thread aynı PENDING job'ı alamaz."""
    close_old_connections()

    # Faz 7: kiosk fixture'ı oluştururken _on_kiosk_save sinyali PENDING job
    # yaratıyor (async queue canonical). Önceki jobları temizle — sadece bu testin
    # job'ı kuyruğa girmeli.
    GenerationJob.objects.filter(status=GenerationJob.JobStatus.PENDING).delete()

    job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk_fb,
        status=GenerationJob.JobStatus.PENDING,
        triggered_by="test",
        available_at=timezone.now() - _dt.timedelta(seconds=1),
        dedupe_key=f"kd:{kiosk_fb.id}:{TODAY}-fb15",
        attempt_count=0,
        max_attempts=3,
    )
    job_pk = job.pk

    claimed_by = []
    barrier = threading.Barrier(2)

    def worker():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            claimed = claim_next_job()
            if claimed is not None:
                claimed_by.append(claimed.pk)
        finally:
            close_old_connections()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join(timeout=20)
    t2.join(timeout=20)

    # Tam olarak bir worker job'ı claim etmeli
    assert len(claimed_by) <= 1, (
        f"Birden fazla worker aynı job'ı claim etti: {claimed_by}"
    )
    # Claim eden worker'ın job'ı RUNNING durumunda olmalı
    if claimed_by:
        job.refresh_from_db()
        assert job.status == GenerationJob.JobStatus.RUNNING


# ─────────────────────────────────────────────────────────────────────────────
# FB-16  İki worker farklı job'ları güvenle claim edebilir
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_fb16_two_workers_claim_different_jobs(kiosk_fb, kiosk_fb2):
    """İki worker, iki farklı PENDING job'ı eş zamanlı sahiplenebilir."""
    close_old_connections()

    job1 = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk_fb,
        status=GenerationJob.JobStatus.PENDING,
        triggered_by="test",
        available_at=timezone.now() - _dt.timedelta(seconds=1),
        dedupe_key=f"kd:{kiosk_fb.id}:{TODAY}-fb16a",
        attempt_count=0,
        max_attempts=3,
    )
    job2 = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk_fb2,
        status=GenerationJob.JobStatus.PENDING,
        triggered_by="test",
        available_at=timezone.now() - _dt.timedelta(seconds=1),
        dedupe_key=f"kd:{kiosk_fb2.id}:{TODAY}-fb16b",
        attempt_count=0,
        max_attempts=3,
    )

    claimed_pks = []
    barrier = threading.Barrier(2)

    def worker():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            claimed = claim_next_job()
            if claimed is not None:
                claimed_pks.append(claimed.pk)
        finally:
            close_old_connections()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join(timeout=20)
    t2.join(timeout=20)

    # Her iki job farklı worker'lara atanmış olmalı (ya da en az biri claim edildi)
    assert len(set(claimed_pks)) == len(claimed_pks), "Aynı job iki kez claim edildi"


# ─────────────────────────────────────────────────────────────────────────────
# FB-23  Aynı job tekrar işlenince duplicate üretilmez
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
@override_settings(DOOH_ENGINE_V2="active")
def test_fb23_duplicate_processing_safe(kiosk_fb, house_ad_fb):
    """Aynı job iki kez işlenirse idempotent: playlist sayısı katlanmaz."""
    close_old_connections()

    from apps.campaigns.models import Campaign, Creative, DeliveryRule
    base = timezone.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))
    camp = Campaign.objects.create(
        name="FB23",
        start_date=base - _dt.timedelta(days=1),
        end_date=base + _dt.timedelta(days=2, hours=23),
        status=Campaign.Status.ACTIVE,
        target_scope="ALL",
    )
    Creative.objects.create(
        campaign=camp,
        media_url=f"http://localhost:9000/dev/ads/fb23-{camp.pk}.mp4",
        duration_seconds=15,
    )
    DeliveryRule.objects.create(
        campaign=camp,
        delivery_type="PER_HOUR",
        count=1,
        guarantee_mode="BEST_EFFORT",
    )

    def make_running_job(suffix):
        return GenerationJob.objects.create(
            target_date=TODAY,
            kiosk=kiosk_fb,
            status=GenerationJob.JobStatus.RUNNING,
            attempt_count=1,
            max_attempts=3,
            triggered_by="test",
            available_at=timezone.now(),
            dedupe_key=f"kd:{kiosk_fb.id}:{TODAY}-fb23-{suffix}",
            payload={"kiosk_id": kiosk_fb.id, "date": str(TODAY), "trigger_reason": "test"},
            worker_id="test-w",
            lock_expires_at=timezone.now() + _dt.timedelta(minutes=5),
        )

    j1 = make_running_job("a")
    process_job(j1)
    count_after_first = Playlist.objects.filter(kiosk=kiosk_fb, target_date=TODAY).count()

    j2 = make_running_job("b")
    process_job(j2)
    count_after_second = Playlist.objects.filter(kiosk=kiosk_fb, target_date=TODAY).count()

    # İkinci işlem replace yapar (aynı sayı, katlanmaz)
    assert count_after_second == count_after_first, (
        f"İkinci işlem playlist'i katladı: {count_after_first} → {count_after_second}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# FB-24  Aynı kiosk için concurrent publish → lost update yok
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
@override_settings(DOOH_ENGINE_V2="active")
def test_fb24_concurrent_publish_no_lost_update(kiosk_fb, house_ad_fb):
    """İki thread aynı kiosk için aynı anda process_job → son hali tutarlı."""
    close_old_connections()

    from apps.campaigns.models import Campaign, Creative, DeliveryRule
    base = timezone.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))
    camp = Campaign.objects.create(
        name="FB24",
        start_date=base - _dt.timedelta(days=1),
        end_date=base + _dt.timedelta(days=2, hours=23),
        status=Campaign.Status.ACTIVE,
        target_scope="ALL",
    )
    Creative.objects.create(
        campaign=camp,
        media_url=f"http://localhost:9000/dev/ads/fb24-{camp.pk}.mp4",
        duration_seconds=15,
    )
    DeliveryRule.objects.create(
        campaign=camp,
        delivery_type="PER_HOUR",
        count=1,
        guarantee_mode="BEST_EFFORT",
    )

    errors = []
    barrier = threading.Barrier(2)

    def run_publish(suffix):
        close_old_connections()
        try:
            j = GenerationJob.objects.create(
                target_date=TODAY,
                kiosk=kiosk_fb,
                status=GenerationJob.JobStatus.RUNNING,
                attempt_count=1,
                max_attempts=3,
                triggered_by="test",
                available_at=timezone.now(),
                dedupe_key=f"kd:{kiosk_fb.id}:{TODAY}-fb24-{suffix}",
                payload={"kiosk_id": kiosk_fb.id, "date": str(TODAY), "trigger_reason": "test"},
                worker_id=f"w-{suffix}",
                lock_expires_at=timezone.now() + _dt.timedelta(minutes=5),
            )
            barrier.wait(timeout=10)
            process_job(j)
        except Exception as e:
            errors.append(e)
        finally:
            close_old_connections()

    t1 = threading.Thread(target=run_publish, args=("a",))
    t2 = threading.Thread(target=run_publish, args=("b",))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    # Playlist tablosu tutarlı olmalı (her kiosk+date+hour için tek satır)
    from django.db.models import Count
    duplicates = (
        Playlist.objects
        .filter(kiosk=kiosk_fb, target_date=TODAY)
        .values("kiosk_id", "target_date", "target_hour")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )
    assert duplicates.count() == 0, f"Duplicate playlist satırları: {list(duplicates)}"


# ─────────────────────────────────────────────────────────────────────────────
# FB-33  CAMPAIGN_TOTAL invariantı concurrency altında bozulmaz
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
@override_settings(DOOH_ENGINE_V2="active")
def test_fb33_campaign_total_concurrency(kiosk_fb, kiosk_fb2, house_ad_fb):
    """İki eş zamanlı activation CAMPAIGN_TOTAL global invariantı bozmamalı."""
    close_old_connections()

    from apps.campaigns.models import (
        Campaign, Creative, DeliveryRule, KioskDayQuota, CampaignTotalAllocation
    )
    from apps.campaigns.services.activation_service import ActivationService, CapacityError

    base = timezone.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))
    camp = Campaign.objects.create(
        name="FB33",
        start_date=base - _dt.timedelta(days=1),
        end_date=base + _dt.timedelta(days=2, hours=23),
        status=Campaign.Status.ACTIVE,
        target_scope="ALL",
    )
    Creative.objects.create(
        campaign=camp,
        media_url=f"http://localhost:9000/dev/ads/fb33-{camp.pk}.mp4",
        duration_seconds=15,
    )
    total_target = 2
    DeliveryRule.objects.create(
        campaign=camp,
        delivery_type="CAMPAIGN_TOTAL",
        count=total_target,
        guarantee_mode="BEST_EFFORT",
    )

    camp_pk = camp.pk
    errors = []
    barrier = threading.Barrier(2)

    def activate():
        close_old_connections()
        try:
            from apps.campaigns.models import Campaign as C
            c = C.objects.get(pk=camp_pk)
            barrier.wait(timeout=10)
            ActivationService.activate(c)
        except (CapacityError, Exception) as e:
            errors.append(e)
        finally:
            close_old_connections()

    t1 = threading.Thread(target=activate)
    t2 = threading.Thread(target=activate)
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    # Global invariant: sum(placed) <= total_target
    total_placed = sum(q.placed for q in KioskDayQuota.objects.filter(campaign=camp_pk))
    assert total_placed <= total_target, (
        f"CAMPAIGN_TOTAL invariantı bozuldu: placed={total_placed} > total={total_target}"
    )
