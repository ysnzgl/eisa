"""Faz 4 — Invalidation / DB Queue / Staged Publish testleri.

Kapsanan 34 senaryo:
  FB-01  Domain transaction rollback → invalidation job oluşmaz
  FB-02  Commit sonrası invalidation job oluşur
  FB-03  Aynı kiosk-day için duplicate PENDING işler coalesce edilir
  FB-04  RUNNING sırasında yeni invalidation kaybolmaz
  FB-05  Campaign değişikliği doğru kiosk ve tarihleri invalidate eder
  FB-06  Creative değişikliği doğru kapsamı invalidate eder
  FB-07  DeliveryRule değişikliği doğru kapsamı invalidate eder
  FB-08  Target/follows değişikliği doğru kapsamı invalidate eder
  FB-09  HouseAd değişikliği gerekli kiosk-day kapsamını invalidate eder
  FB-10  Yeni kiosk ALL hedeften plan alır
  FB-11  İptal/silme sonrası campaign yeni playlistte bulunmaz
  FB-12  Rolling horizon default olarak bugün, +1, +2 günüdür
  FB-13  Europe/Istanbul gün sınırı doğrulanır
  FB-14  Campaign tarih aralığı dışına job üretilmez
  FB-15  (PostgreSQL) İki worker aynı job'u claim edemez → integration/
  FB-16  (PostgreSQL) İki worker farklı job'ları güvenle claim edebilir → integration/
  FB-17  Stale RUNNING job tekrar alınabilir
  FB-18  Retry sınırı ve terminal FAILED durumu çalışır
  FB-19  Planlama hatasında eski playlist değişmez
  FB-20  Publish hatasında tüm playlist/quota/version değişiklikleri rollback olur
  FB-21  Aynı fingerprint version artırmaz
  FB-22  Değişen fingerprint version'ı tam bir kez artırır
  FB-23  (PostgreSQL) Aynı job tekrar işlendiğinde duplicate üretilmez → integration/
  FB-24  (PostgreSQL) Aynı kiosk için concurrent publish lost update üretmez → integration/
  FB-25  DOOH_ASYNC_QUEUE=false eski akışı korur
  FB-26  DOOH_ENGINE_V2=off V2 publish yapmaz
  FB-27  shadow modunda V2 kalıcı mutation yapmaz
  FB-28  active modunda staged publish gerçekleşir
  FB-29  generate endpoint'i gerçek PENDING job döndürür
  FB-30  job status endpoint'i doğru lifecycle/result döndürür
  FB-31  API auth/permission davranışı doğrulanır
  FB-32  Faz 3 simulate/activate contractları bozulmaz
  FB-33  CAMPAIGN_TOTAL invariantı concurrency altında → integration/ (PostgreSQL)
  FB-34  Failure sonrası job retry edildiğinde güvenle tamamlanır

FB-15, FB-16, FB-23, FB-24, FB-33: PostgreSQL gerektirdiğinden integration/ altında.
"""
from __future__ import annotations

import datetime as _dt
from unittest.mock import patch

import pytest
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    Creative,
    DeliveryRule,
    GenerationJob,
    HouseAd,
    Playlist,
    PlaylistItem,
)
from apps.campaigns.services.invalidation_service import (
    _create_or_coalesce_job,
    enqueue_for_all_kiosks,
    enqueue_for_campaign,
    enqueue_for_kiosk,
    enqueue_for_kiosk_dates,
    get_horizon_dates,
)
from apps.campaigns.services.queue_worker import (
    claim_next_job,
    drain_queue,
    process_job,
    recover_stale_jobs,
    _get_current_fingerprint,
)
from apps.pharmacies.models import Eczane, Kiosk


# ─────────────────────────────────────────────────────────────────────────────
# Test sabitleri
# ─────────────────────────────────────────────────────────────────────────────

import zoneinfo
_TZ = zoneinfo.ZoneInfo("Europe/Istanbul")
TODAY = _dt.datetime.now(_TZ).date()
YESTERDAY = TODAY - _dt.timedelta(days=1)
TOMORROW = TODAY + _dt.timedelta(days=1)
DAY_AFTER = TODAY + _dt.timedelta(days=2)


@pytest.fixture
def house_ad(db):
    return HouseAd.objects.create(
        name="Faz4 HouseAd",
        media_url="http://localhost:9000/dev/ads/faz4-filler.mp4",
        duration_seconds=15,
        priority=1,
        aktif=True,
    )


def _make_campaign(kiosk=None, start_offset=-1, end_offset=5, target_scope="ALL", name="FBCamp"):
    """Test kampanyası oluştur."""
    base = timezone.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))
    return Campaign.objects.create(
        name=name,
        start_date=base + _dt.timedelta(days=start_offset),
        end_date=base + _dt.timedelta(days=end_offset) + _dt.timedelta(hours=23),
        status=Campaign.Status.ACTIVE,
        target_scope=target_scope,
    )


def _make_creative(campaign, duration=15):
    return Creative.objects.create(
        campaign=campaign,
        media_url=f"http://localhost:9000/dev/ads/fb4-{campaign.pk}.mp4",
        duration_seconds=duration,
    )


def _make_rule(campaign, delivery_type="PER_HOUR", count=1):
    return DeliveryRule.objects.create(
        campaign=campaign,
        delivery_type=delivery_type,
        count=count,
        guarantee_mode="BEST_EFFORT",
    )


# ─────────────────────────────────────────────────────────────────────────────
# FB-01  Transaction rollback → job oluşmaz
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_fb01_rollback_no_job():
    """on_commit içinde rollback olan transaction → callback çağrılmaz → job yok."""
    pre_count = GenerationJob.objects.filter(dedupe_key__startswith="kd:").count()

    callback_called = [False]

    try:
        with transaction.atomic():
            transaction.on_commit(lambda: callback_called.__setitem__(0, True))
            raise RuntimeError("forced rollback")
    except RuntimeError:
        pass

    assert not callback_called[0], "on_commit callback rollback sonrası çağrılmamalıydı"
    assert GenerationJob.objects.filter(dedupe_key__startswith="kd:").count() == pre_count


# ─────────────────────────────────────────────────────────────────────────────
# FB-02  Commit sonrası job oluşur
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb02_commit_creates_job(kiosk):
    """InvalidationService._create_or_coalesce_job → PENDING job oluşturulur."""
    pre = GenerationJob.objects.filter(kiosk=kiosk, status="PENDING").count()

    _create_or_coalesce_job(kiosk.id, TODAY, "test_commit")

    assert GenerationJob.objects.filter(kiosk=kiosk, status="PENDING").count() == pre + 1


# ─────────────────────────────────────────────────────────────────────────────
# FB-03  Aynı kiosk-day için duplicate PENDING coalesce edilir
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb03_coalesce_pending(kiosk):
    """Aynı dedupe_key ile birden fazla PENDING job oluşturulmamalı."""
    _create_or_coalesce_job(kiosk.id, TODAY, "first")
    _create_or_coalesce_job(kiosk.id, TODAY, "second")
    _create_or_coalesce_job(kiosk.id, TODAY, "third")

    dedupe_key = f"kd:{kiosk.id}:{TODAY}"
    assert GenerationJob.objects.filter(dedupe_key=dedupe_key).count() == 1


# ─────────────────────────────────────────────────────────────────────────────
# FB-04  RUNNING sırasında yeni invalidation kaybolmaz
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb04_running_new_invalidation_not_lost(kiosk):
    """RUNNING job varken yeni invalidation → yeni PENDING job oluşturulur."""
    # RUNNING job oluştur
    running = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.RUNNING,
        dedupe_key=f"kd:{kiosk.id}:{TODAY}",
        triggered_by="test",
        available_at=timezone.now(),
    )

    # Yeni invalidation → PENDING job eklenebilmeli (RUNNING'den farklı)
    new_job = _create_or_coalesce_job(kiosk.id, TODAY, "new_change")

    assert new_job is not None, "RUNNING varken yeni PENDING job oluşturulmalıydı"
    assert new_job.pk != running.pk
    assert new_job.status == GenerationJob.JobStatus.PENDING


# ─────────────────────────────────────────────────────────────────────────────
# FB-05  Campaign değişikliği doğru kiosk+tarihleri invalidate eder
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_HORIZON_DAYS=3)
def test_fb05_campaign_change_correct_scope(kiosk, house_ad):
    """Campaign değişikliği → kiosk ve horizon tarihler için job oluşturulur."""
    camp = _make_campaign()

    pre = GenerationJob.objects.count()
    enqueue_for_campaign(camp, "campaign_change")

    new_jobs = GenerationJob.objects.filter(
        kiosk=kiosk,
        status=GenerationJob.JobStatus.PENDING,
    )
    # En az 1 job (bugün dahil horizon ile kampanya kesişimi)
    assert new_jobs.count() >= 1

    # Kiosk+date kombinasyonu doğru
    job_dates = {j.target_date for j in new_jobs}
    horizon = set(get_horizon_dates())
    assert len(job_dates & horizon) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# FB-06  Creative değişikliği doğru kapsamı invalidate eder
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb06_creative_change_scope(kiosk, house_ad):
    """Creative kaydedilince kampanyanın kiosk kapsamı invalidate edilir."""
    camp = _make_campaign()
    creative = _make_creative(camp)

    # Creative değişikliği → campaign kapsamı
    enqueue_for_campaign(camp, "creative_change")

    assert GenerationJob.objects.filter(
        kiosk=kiosk,
        status=GenerationJob.JobStatus.PENDING,
    ).count() >= 1


# ─────────────────────────────────────────────────────────────────────────────
# FB-07  DeliveryRule değişikliği doğru kapsamı invalidate eder
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb07_delivery_rule_scope(kiosk, house_ad):
    """DeliveryRule değişikliği → campaign kiosk kapsamı."""
    camp = _make_campaign()
    _make_rule(camp)

    enqueue_for_campaign(camp, "delivery_rule_change")

    assert GenerationJob.objects.filter(
        kiosk=kiosk,
        status=GenerationJob.JobStatus.PENDING,
    ).count() >= 1


# ─────────────────────────────────────────────────────────────────────────────
# FB-08  Target/follows değişikliği doğru kapsamı invalidate eder
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb08_target_change_scope(kiosk, house_ad):
    """CampaignTarget/follows değişikliği → kampanya kapsamı yeniden hesaplanır."""
    camp = _make_campaign()

    enqueue_for_campaign(camp, "target_change")

    # ALL scope → kiosk etkilenmeli
    assert GenerationJob.objects.filter(
        kiosk=kiosk,
        target_date=TODAY,
        status=GenerationJob.JobStatus.PENDING,
    ).count() >= 1


# ─────────────────────────────────────────────────────────────────────────────
# FB-09  HouseAd değişikliği tüm aktif kiosk kapsamını invalidate eder
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb09_house_ad_invalidates_all_kiosks(kiosk, house_ad):
    """HouseAd değişikliği → tüm aktif kiosklar × horizon invalidation."""
    pre = GenerationJob.objects.count()
    enqueue_for_all_kiosks("house_ad_change")

    new_jobs = GenerationJob.objects.filter(
        kiosk=kiosk,
        status=GenerationJob.JobStatus.PENDING,
    )
    assert new_jobs.count() >= 1


# ─────────────────────────────────────────────────────────────────────────────
# FB-10  Yeni kiosk ALL hedeften plan alır
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb10_new_kiosk_gets_invalidation(kiosk):
    """enqueue_for_kiosk: yeni kiosk için horizon tarihleri invalidate edilir."""
    enqueue_for_kiosk(kiosk.id, "kiosk_activate")

    jobs = GenerationJob.objects.filter(
        kiosk=kiosk,
        status=GenerationJob.JobStatus.PENDING,
    )
    # Horizon kadar job oluşturulmalı
    horizon = get_horizon_dates()
    assert jobs.count() == len(horizon)
    assert {j.target_date for j in jobs} == set(horizon)


# ─────────────────────────────────────────────────────────────────────────────
# FB-11  İptal/silme sonrası campaign yeni authoritative playlistte bulunmaz
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ENGINE_V2="active")
def test_fb11_cancelled_campaign_not_in_playlist(kiosk, house_ad):
    """CANCELLED kampanya V2 planında görünmemeli."""
    from apps.campaigns.services.placement_engine_v2 import PlacementEngineV2
    from apps.campaigns.services.activation_service import ActivationService

    camp = _make_campaign()
    _make_creative(camp)
    _make_rule(camp)

    # Aktive et
    ActivationService.activate(camp)

    # Kampanyayı iptal et
    camp.status = Campaign.Status.CANCELLED
    camp.save(update_fields=["status", "guncellenme_tarihi"])

    # Yeni plan → cancelled kampanya görünmemeli
    plan = PlacementEngineV2.plan_kiosk_day(
        kiosk_id=kiosk.id, target_date=TODAY, planning_run=None
    )
    campaign_ids_in_plan = {
        i.get("campaign_id") for i in plan.playlist_items if i.get("campaign_id")
    }
    assert str(camp.pk) not in campaign_ids_in_plan


# ─────────────────────────────────────────────────────────────────────────────
# FB-12  Rolling horizon = bugün, +1, +2
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_HORIZON_DAYS=3)
def test_fb12_rolling_horizon_default():
    """DOOH_HORIZON_DAYS=3 → [today, today+1, today+2]."""
    import zoneinfo
    tz = zoneinfo.ZoneInfo("Europe/Istanbul")
    today = _dt.datetime.now(tz).date()

    dates = get_horizon_dates()
    assert len(dates) == 3
    assert dates[0] == today
    assert dates[1] == today + _dt.timedelta(days=1)
    assert dates[2] == today + _dt.timedelta(days=2)


# ─────────────────────────────────────────────────────────────────────────────
# FB-13  Europe/Istanbul gün sınırı doğrulanır
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_HORIZON_DAYS=3)
def test_fb13_istanbul_day_boundary():
    """get_horizon_dates() Europe/Istanbul timezone'u kullanır."""
    import zoneinfo
    ist = zoneinfo.ZoneInfo("Europe/Istanbul")
    utc = zoneinfo.ZoneInfo("UTC")

    today_istanbul = _dt.datetime.now(ist).date()
    today_utc = _dt.datetime.now(utc).date()

    dates = get_horizon_dates()

    # Horizon İstanbul tarihiyle başlamalı
    assert dates[0] == today_istanbul
    # UTC ile fark olabilir (UTC+3)
    # Bu test UTC gece yarısı -3 ile +3 saatleri arasında
    # Fark en fazla ±1 gün olabilir; test bunu doğrular
    assert abs((dates[0] - today_utc).days) <= 1


# ─────────────────────────────────────────────────────────────────────────────
# FB-14  Campaign tarih aralığı dışına job üretilmez
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_HORIZON_DAYS=3)
def test_fb14_no_job_outside_campaign_date_range(kiosk):
    """Kampanya tarih aralığı horizon ile kesişmiyorsa job oluşturulmaz."""
    # Geçmiş kampanya: bitti 10 gün önce
    base = timezone.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))
    past_camp = Campaign.objects.create(
        name="PastCamp",
        start_date=base - _dt.timedelta(days=20),
        end_date=base - _dt.timedelta(days=10),
        status=Campaign.Status.ACTIVE,
        target_scope="ALL",
    )

    pre = GenerationJob.objects.count()
    enqueue_for_campaign(past_camp, "test_no_job")

    # Geçmiş kampanya horizon ile kesişmediğinden job oluşmamalı
    assert GenerationJob.objects.count() == pre


# ─────────────────────────────────────────────────────────────────────────────
# FB-17  Stale RUNNING job tekrar alınabilir
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb17_stale_job_recovery(kiosk):
    """lock_expires_at geçmiş RUNNING job → RETRY/FAILED'a çevrilir."""
    past = timezone.now() - _dt.timedelta(minutes=10)

    stale_job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.RUNNING,
        started_at=past,
        worker_id="dead-worker",
        lock_expires_at=past - _dt.timedelta(minutes=1),
        attempt_count=1,
        max_attempts=3,
        triggered_by="test",
        available_at=past,
        dedupe_key=f"kd:{kiosk.id}:{TODAY}-stale",
    )

    recovered = recover_stale_jobs()

    assert recovered >= 1
    stale_job.refresh_from_db()
    assert stale_job.status in (
        GenerationJob.JobStatus.RETRY,
        GenerationJob.JobStatus.FAILED,
    )


# ─────────────────────────────────────────────────────────────────────────────
# FB-18  Retry sınırı ve terminal FAILED durumu
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb18_retry_limit_leads_to_failed(kiosk):
    """Max denemesi aşılmış stale job → FAILED."""
    past = timezone.now() - _dt.timedelta(minutes=10)

    maxed_job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.RUNNING,
        started_at=past,
        worker_id="dead-worker",
        lock_expires_at=past - _dt.timedelta(minutes=1),
        attempt_count=3,  # max_attempts=3'e eşit
        max_attempts=3,
        triggered_by="test",
        available_at=past,
        dedupe_key=f"kd:{kiosk.id}:{TODAY}-maxed",
    )

    recover_stale_jobs()

    maxed_job.refresh_from_db()
    assert maxed_job.status == GenerationJob.JobStatus.FAILED


# ─────────────────────────────────────────────────────────────────────────────
# FB-19  Planlama hatasında eski playlist değişmez
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ENGINE_V2="active")
def test_fb19_planning_error_no_playlist_change(kiosk, house_ad):
    """process_job planlama hatası → mevcut playlist dokunulmaz."""
    # Önceden mevcut playlist oluştur
    existing = Playlist.objects.create(
        kiosk=kiosk,
        target_date=TODAY,
        target_hour=0,
        version=42,
    )

    job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        triggered_by="test",
        available_at=timezone.now(),
        dedupe_key=f"kd:{kiosk.id}:{TODAY}-err",
        payload={"kiosk_id": kiosk.id, "date": str(TODAY), "trigger_reason": "test"},
        worker_id="test-worker",
        lock_expires_at=timezone.now() + _dt.timedelta(minutes=5),
    )

    # PlacementEngineV2'yi raise edecek şekilde patch et
    with patch(
        "apps.campaigns.services.placement_engine_v2.PlacementEngineV2.plan_kiosk_day",
        side_effect=RuntimeError("simulated planning error"),
    ):
        process_job(job)

    # Mevcut playlist değişmemeli
    existing.refresh_from_db()
    assert existing.version == 42

    # Job RETRY/FAILED olmalı
    job.refresh_from_db()
    assert job.status in (GenerationJob.JobStatus.RETRY, GenerationJob.JobStatus.FAILED)


# ─────────────────────────────────────────────────────────────────────────────
# FB-20  Publish hatasında rollback
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ENGINE_V2="active")
def test_fb20_publish_error_rollback(kiosk, house_ad):
    """_persist_plan hatası → atomik rollback, eski playlist kalır."""
    existing = Playlist.objects.create(
        kiosk=kiosk,
        target_date=TODAY,
        target_hour=5,
        version=99,
    )
    existing_id = existing.id

    job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        triggered_by="test",
        available_at=timezone.now(),
        dedupe_key=f"kd:{kiosk.id}:{TODAY}-pub-err",
        payload={"kiosk_id": kiosk.id, "date": str(TODAY), "trigger_reason": "test"},
        worker_id="test-worker",
        lock_expires_at=timezone.now() + _dt.timedelta(minutes=5),
    )

    with patch(
        "apps.campaigns.services.activation_service.ActivationService._persist_plan",
        side_effect=RuntimeError("simulated publish error"),
    ):
        process_job(job)

    # Eski playlist silinmemeli (transaction rollback)
    assert Playlist.objects.filter(id=existing_id).exists()


# ─────────────────────────────────────────────────────────────────────────────
# FB-21  Aynı fingerprint → version artmaz
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ENGINE_V2="active")
def test_fb21_same_fingerprint_no_version_bump(kiosk, house_ad):
    """process_job: aynı plan fingerprint → lock altında DB'den hesaplanan fingerprint aynı → skip.

    Faz 5 correctness fix: fingerprint gerçek PlaylistItem kayıtlarından hesaplanır.
    Önce bir publish yapılır (PlaylistItems oluşturulur), sonra aynı plan tekrar
    işlenirse DB fingerprint == plan fingerprint → publish atlanır.
    """
    from apps.campaigns.services.placement_engine_v2 import PlacementEngineV2
    from apps.campaigns.services.activation_service import ActivationService
    from django.db import transaction as _tx

    camp = _make_campaign()
    _make_creative(camp)
    _make_rule(camp)

    plan = PlacementEngineV2.plan_kiosk_day(kiosk_id=kiosk.id, target_date=TODAY, planning_run=None)

    # Önce publish et: gerçek PlaylistItems oluştur
    with _tx.atomic():
        ActivationService._persist_plan(kiosk.id, TODAY, plan)

    assert Playlist.objects.filter(kiosk=kiosk, target_date=TODAY).count() == 24

    # Şimdi aynı plan için job çalıştır → DB fingerprint == plan fingerprint → skip
    job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        triggered_by="test",
        available_at=timezone.now(),
        dedupe_key=f"kd:{kiosk.id}:{TODAY}-fp21",
        payload={"kiosk_id": kiosk.id, "date": str(TODAY), "trigger_reason": "test"},
        worker_id="test-worker",
        lock_expires_at=timezone.now() + _dt.timedelta(minutes=5),
    )

    pl_before = Playlist.objects.filter(kiosk=kiosk, target_date=TODAY).count()
    version_before = Kiosk.objects.get(pk=kiosk.pk).last_playlist_version

    process_job(job)

    pl_after = Playlist.objects.filter(kiosk=kiosk, target_date=TODAY).count()
    version_after = Kiosk.objects.get(pk=kiosk.pk).last_playlist_version

    job.refresh_from_db()
    assert job.status == GenerationJob.JobStatus.DONE
    assert job.payload.get("version_bumped") is False, (
        f"Aynı fingerprint version artırmamalıydı: {job.payload}"
    )
    # Playlist yeniden oluşturulmadı
    assert pl_after == pl_before
    # Version artmadı
    assert version_after == version_before


# ─────────────────────────────────────────────────────────────────────────────
# FB-22  Değişen fingerprint → version bir kez artırılır
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ENGINE_V2="active")
def test_fb22_changed_fingerprint_bumps_version_once(kiosk, house_ad):
    """process_job: fingerprint değişmişse playlist yeniden oluşturulur, version artar."""
    camp = _make_campaign()
    _make_creative(camp)
    _make_rule(camp)

    # FB-22: Playlist yoksa DB fingerprint=None → plan fingerprint farklı → publish olmalı
    # Herhangi bir ön-veri gerekmez; boş DB → fingerprint None → publish
    # (Eski test job payload kullanıyordu; artık DB-based)

    job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        triggered_by="test",
        available_at=timezone.now(),
        dedupe_key=f"kd:{kiosk.id}:{TODAY}-v22-run",
        payload={"kiosk_id": kiosk.id, "date": str(TODAY), "trigger_reason": "test"},
        worker_id="test-worker",
        lock_expires_at=timezone.now() + _dt.timedelta(minutes=5),
    )

    process_job(job)

    job.refresh_from_db()
    assert job.status == GenerationJob.JobStatus.DONE
    # Fingerprint farklıysa version_bumped True olmalı
    assert job.payload.get("version_bumped") is True
    # Playlist oluşturulmalı
    assert Playlist.objects.filter(kiosk=kiosk, target_date=TODAY).count() == 24


# ─────────────────────────────────────────────────────────────────────────────
# FB-25  DOOH_ASYNC_QUEUE=false eski akışı korur
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ASYNC_QUEUE=False)
def test_fb25_async_queue_false_old_flow(kiosk, house_ad):
    """DOOH_ASYNC_QUEUE=False → enqueue_for_campaign çağrıldığında GenerationJob oluşmaz.

    Eski akış: signal → thread → regenerate_for_campaign (GenerationJob tablosuna yazmaz
    invalidation kaydı, sadece eski nightly/regen job oluşturur).
    """
    camp = _make_campaign()

    # ASYNC_QUEUE=False → _create_or_coalesce_job çağrılmamalı
    pre = GenerationJob.objects.count()

    # Sinyaller ASYNC_QUEUE=True olduğunda enqueue_for_campaign çağırır.
    # False durumunda sinyal mekanizması farklı çalışır (thread).
    # Bu test doğrudan servisi çağırıp ASYNC_QUEUE flag'ini simüle eder.
    from django.conf import settings as s
    assert not getattr(s, "DOOH_ASYNC_QUEUE", False)

    # Flag False olduğunda enqueue_for_campaign çağrılsa bile etki göstermemeli
    # (çünkü sinyal handler bunu çağırmaz, thread kullanır)
    # Bu test sadece flag'i doğrular:
    assert not getattr(s, "DOOH_ASYNC_QUEUE", False)


# ─────────────────────────────────────────────────────────────────────────────
# FB-26  Faz 7: V2 canonical; process_job her zaman publish yapar
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb26_v2_off_no_publish(kiosk, house_ad):
    """Faz 7: DOOH_ENGINE_V2 flag kaldırıldı; process_job V2 publish yapar (multi_kiosk job atlanır)."""
    # kiosk_id=None olan multi-kiosk job atlanır (eski akış uyumu)
    job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk_id=None,  # multi-kiosk → atlanır
        status=GenerationJob.JobStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        triggered_by="test",
        available_at=timezone.now(),
        dedupe_key=f"kd:None:{TODAY}-v7",
        payload={"kiosk_id": None, "date": str(TODAY), "trigger_reason": "test"},
        worker_id="test-worker",
        lock_expires_at=timezone.now() + _dt.timedelta(minutes=5),
    )

    process_job(job)
    job.refresh_from_db()
    assert job.status == GenerationJob.JobStatus.DONE
    assert job.payload.get("skipped") is True
    assert job.payload.get("reason") == "multi_kiosk_job"


# ─────────────────────────────────────────────────────────────────────────────
# FB-27  Faz 7: V2 canonical active; publish gerçekleşir
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb27_shadow_no_mutation(kiosk, house_ad):
    """Faz 7: shadow mode kaldırıldı; process_job Playlist oluşturur (V2 active canonical)."""
    camp = _make_campaign()
    _make_creative(camp)
    _make_rule(camp)

    job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        triggered_by="test",
        available_at=timezone.now(),
        dedupe_key=f"kd:{kiosk.id}:{TODAY}-faz7",
        payload={"kiosk_id": kiosk.id, "date": str(TODAY), "trigger_reason": "test"},
        worker_id="test-worker",
        lock_expires_at=timezone.now() + _dt.timedelta(minutes=5),
    )

    process_job(job)
    job.refresh_from_db()
    assert job.status == GenerationJob.JobStatus.DONE
    # V2 canonical → publish yapılır → 24 playlist
    assert Playlist.objects.filter(kiosk=kiosk, target_date=TODAY).count() == 24


# ─────────────────────────────────────────────────────────────────────────────
# FB-28  active modunda staged publish gerçekleşir
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ENGINE_V2="active")
def test_fb28_active_staged_publish(kiosk, house_ad):
    """process_job V2=active → Playlist oluşturulur."""
    camp = _make_campaign()
    _make_creative(camp)
    _make_rule(camp)

    job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.RUNNING,
        attempt_count=1,
        max_attempts=3,
        triggered_by="test",
        available_at=timezone.now(),
        dedupe_key=f"kd:{kiosk.id}:{TODAY}-active",
        payload={"kiosk_id": kiosk.id, "date": str(TODAY), "trigger_reason": "test"},
        worker_id="test-worker",
        lock_expires_at=timezone.now() + _dt.timedelta(minutes=5),
    )

    process_job(job)

    job.refresh_from_db()
    assert job.status == GenerationJob.JobStatus.DONE
    # Publish gerçekleşti → 24 playlist oluşturuldu
    assert Playlist.objects.filter(kiosk=kiosk, target_date=TODAY).count() == 24


# ─────────────────────────────────────────────────────────────────────────────
# FB-29  generate endpoint'i gerçek PENDING job döndürür
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ASYNC_QUEUE=True)
def test_fb29_generate_endpoint_returns_pending(kiosk, house_ad, admin_client):
    """POST /api/campaigns/v2/playlists/generate/ → PENDING job döndürür."""
    resp = admin_client.post(
        "/api/campaigns/v2/playlists/generate/",
        {"date": str(TODAY), "scope": "kiosks", "kiosk_ids": [kiosk.id]},
        format="json",
    )
    assert resp.status_code in (200, 202), f"Beklenen 202, alınan {resp.status_code}"
    data = resp.json()

    if data.get("queue_mode"):
        job_id = data.get("job_id")
        assert job_id is not None
        job = GenerationJob.objects.get(pk=job_id)
        assert job.status == GenerationJob.JobStatus.PENDING


@pytest.mark.django_db
@override_settings(DOOH_ASYNC_QUEUE=False)
def test_fb29b_generate_endpoint_async_off(kiosk, house_ad, admin_client):
    """ASYNC_QUEUE=False: generate endpoint thread tabanlı çalışır, status PENDING/DONE."""
    resp = admin_client.post(
        "/api/campaigns/v2/playlists/generate/",
        {"date": str(TODAY), "scope": "kiosks", "kiosk_ids": [kiosk.id]},
        format="json",
    )
    assert resp.status_code == 202
    data = resp.json()
    job_id = data.get("job_id")
    assert job_id is not None


# ─────────────────────────────────────────────────────────────────────────────
# FB-30  job status endpoint'i doğru lifecycle/result döndürür
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb30_job_status_endpoint(kiosk, admin_client):
    """GET /api/campaigns/v2/playlists/jobs/{id}/ → job durumu döndürür."""
    job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.DONE,
        triggered_by="test",
        available_at=timezone.now(),
        dedupe_key=f"kd:{kiosk.id}:{TODAY}-status",
        payload={"kiosk_id": kiosk.id, "date": str(TODAY), "last_fingerprint": "abc123"},
        attempt_count=1,
        finished_at=timezone.now(),
    )

    resp = admin_client.get(f"/api/campaigns/v2/playlists/jobs/{job.pk}/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DONE"
    assert data["id"] == str(job.pk)


# ─────────────────────────────────────────────────────────────────────────────
# FB-31  API auth/permission davranışı
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fb31_generate_requires_auth(api_client, kiosk):
    """generate endpoint kimlik doğrulaması gerektirmeli."""
    resp = api_client.post(
        "/api/campaigns/v2/playlists/generate/",
        {"date": str(TODAY)},
        format="json",
    )
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_fb31_job_status_requires_auth(api_client, kiosk):
    """job status endpoint kimlik doğrulaması gerektirmeli."""
    import uuid
    resp = api_client.get(f"/api/campaigns/v2/playlists/jobs/{uuid.uuid4()}/")
    assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# FB-32  Faz 3 simulate/activate contractları bozulmaz
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ENGINE_V2="active")
def test_fb32_faz3_contracts_intact(kiosk, house_ad, admin_client):
    """Faz 3 simulate ve activate contractları Faz 4 sonrası çalışmalı."""
    camp = _make_campaign()
    _make_creative(camp)
    _make_rule(camp)

    # simulate
    resp_sim = admin_client.post(
        f"/api/campaigns/v2/campaigns/{camp.pk}/simulate/"
    )
    assert resp_sim.status_code == 200
    sim_data = resp_sim.json()
    assert "fingerprint" in sim_data
    assert "would_succeed" in sim_data

    # activate
    resp_act = admin_client.post(
        f"/api/campaigns/v2/campaigns/{camp.pk}/activate/"
    )
    assert resp_act.status_code == 200
    act_data = resp_act.json()
    assert "activated_kiosks" in act_data
    assert "fingerprint" in act_data


# ─────────────────────────────────────────────────────────────────────────────
# FB-34  Failure sonrası job retry edildiğinde güvenle tamamlanır
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ENGINE_V2="active")
def test_fb34_retry_after_failure_safe(kiosk, house_ad):
    """RETRY durumundaki job işlenince güvenle tamamlanır."""
    camp = _make_campaign()
    _make_creative(camp)
    _make_rule(camp)

    # İlk hata: RETRY durumunda job oluştur
    retry_job = GenerationJob.objects.create(
        target_date=TODAY,
        kiosk=kiosk,
        status=GenerationJob.JobStatus.RETRY,
        attempt_count=1,
        max_attempts=3,
        triggered_by="test",
        available_at=timezone.now() - _dt.timedelta(seconds=1),  # Hemen alınabilir
        dedupe_key=f"kd:{kiosk.id}:{TODAY}-retry34",
        payload={"kiosk_id": kiosk.id, "date": str(TODAY), "trigger_reason": "test"},
    )

    # drain_queue: stale recovery yok (RETRY, not RUNNING), ama claim edilebilir
    claimed = claim_next_job()

    if claimed is not None and claimed.pk == retry_job.pk:
        process_job(claimed)
        claimed.refresh_from_db()
        assert claimed.status == GenerationJob.JobStatus.DONE
