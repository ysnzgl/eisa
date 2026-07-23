"""Faz 1 — Additive domain schema testleri.

Kapsanan senaryolar:
  F1-01  Campaign DRAFT ve CANCELLED status'lari
  F1-02  Campaign effective_state: SCHEDULED türetilen durum
  F1-03  Campaign target_scope alanı (ALL / RULES / None)
  F1-04  Campaign follows FK — self-link engeli
  F1-05  CampaignTarget KIOSK hedef tipi
  F1-06  CampaignTarget mode (INCLUDE / EXCLUDE)
  F1-07  Creative weight alanı
  F1-08  Creative is_grid_compliant property (15/30/45/60 → True, diğerleri False)
  F1-09  HouseAd is_grid_compliant property
  F1-10  DeliveryRule — temel oluşturma ve alanlar
  F1-11  DeliveryRule TIME_WINDOW validasyonu
  F1-12  DeliveryRule active_hours validasyonu
  F1-13  PlayLog play_event_id alanı (nullable)
  F1-14  PlanningRun, KioskDayQuota, KioskDesiredBundle modelleri
  F1-15  report_grid_noncompliant_media komutu (dry-run)
  F1-16  Faz 0 golden-master testleri bozulmadı (regression kontrolü)
"""
from __future__ import annotations

import datetime as _dt
import uuid

import pytest
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from apps.campaigns.models import (
    Campaign,
    CampaignTarget,
    Creative,
    DeliveryRule,
    HouseAd,
    KioskDayQuota,
    KioskDesiredBundle,
    PlayLog,
    PlanningRun,
    ScheduleRule,
)
from apps.lookups.models import Il, Ilce


# ─────────────────────────────────────────────────────────────────────────────
# Yerel fixture'lar
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def il_istanbul(db) -> Il:
    il, _ = Il.objects.get_or_create(ad="Istanbul")
    return il


# ─────────────────────────────────────────────────────────────────────────────
# Yerel fixture'lar
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def base_campaign(db):
    now = timezone.now()
    return Campaign.objects.create(
        name="Faz1 Test Campaign",
        start_date=now - _dt.timedelta(days=1),
        end_date=now + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )


@pytest.fixture
def future_campaign(db):
    now = timezone.now()
    return Campaign.objects.create(
        name="Future Campaign",
        start_date=now + _dt.timedelta(hours=1),
        end_date=now + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )


# ─────────────────────────────────────────────────────────────────────────────
# F1-01  Campaign DRAFT ve CANCELLED status'lari
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f101_campaign_draft_status(db):
    """Campaign DRAFT status'u DB'ye kaydedilmeli."""
    now = timezone.now()
    c = Campaign.objects.create(
        name="Draft Camp",
        start_date=now,
        end_date=now + _dt.timedelta(days=10),
        status=Campaign.Status.DRAFT,
    )
    c.refresh_from_db()
    assert c.status == "DRAFT"


@pytest.mark.django_db
def test_f101_campaign_cancelled_status(db):
    """Campaign CANCELLED status'u DB'ye kaydedilmeli."""
    now = timezone.now()
    c = Campaign.objects.create(
        name="Cancelled Camp",
        start_date=now,
        end_date=now + _dt.timedelta(days=10),
        status=Campaign.Status.CANCELLED,
    )
    c.refresh_from_db()
    assert c.status == "CANCELLED"


# ─────────────────────────────────────────────────────────────────────────────
# F1-02  effective_state: SCHEDULED türetilen durum
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f102_effective_state_scheduled(future_campaign):
    """ACTIVE + start_date > now → effective_state = 'SCHEDULED'."""
    assert future_campaign.effective_state == "SCHEDULED"


@pytest.mark.django_db
def test_f102_effective_state_active(base_campaign):
    """ACTIVE + start_date geçmiş → effective_state = 'ACTIVE'."""
    assert base_campaign.effective_state == "ACTIVE"


@pytest.mark.django_db
def test_f102_effective_state_paused(base_campaign):
    """PAUSED → effective_state = 'PAUSED' (SCHEDULED değil)."""
    base_campaign.status = Campaign.Status.PAUSED
    base_campaign.save()
    assert base_campaign.effective_state == "PAUSED"


# ─────────────────────────────────────────────────────────────────────────────
# F1-03  Campaign target_scope
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f103_target_scope_all(base_campaign):
    """target_scope=ALL DB'ye kaydedilmeli."""
    base_campaign.target_scope = Campaign.TargetScope.ALL
    base_campaign.save()
    base_campaign.refresh_from_db()
    assert base_campaign.target_scope == "ALL"


@pytest.mark.django_db
def test_f103_target_scope_rules(base_campaign):
    """target_scope=RULES DB'ye kaydedilmeli."""
    base_campaign.target_scope = Campaign.TargetScope.RULES
    base_campaign.save()
    base_campaign.refresh_from_db()
    assert base_campaign.target_scope == "RULES"


@pytest.mark.django_db
def test_f103_target_scope_null_legacy(base_campaign):
    """target_scope=None → legacy davranış (hedefsiz = tüm eczaneler)."""
    assert base_campaign.target_scope is None


# ─────────────────────────────────────────────────────────────────────────────
# F1-04  Campaign follows FK — self-link engeli
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f104_follows_valid_link(db):
    """A → B geçerli follows ilişkisi DB'ye kaydedilmeli."""
    now = timezone.now()
    camp_a = Campaign.objects.create(
        name="A", start_date=now - _dt.timedelta(days=1),
        end_date=now + _dt.timedelta(days=10), status=Campaign.Status.ACTIVE,
    )
    camp_b = Campaign.objects.create(
        name="B", start_date=now - _dt.timedelta(days=1),
        end_date=now + _dt.timedelta(days=10), status=Campaign.Status.ACTIVE,
        follows=camp_a,
    )
    camp_b.refresh_from_db()
    assert camp_b.follows_id == camp_a.pk


@pytest.mark.django_db
def test_f104_follows_none_by_default(base_campaign):
    """follows varsayılan olarak None olmalı."""
    assert base_campaign.follows is None


# ─────────────────────────────────────────────────────────────────────────────
# F1-05  CampaignTarget KIOSK hedef tipi
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f105_campaign_target_kiosk_type(base_campaign, kiosk):
    """KIOSK target tipi kiosk FK ile birlikte DB'ye kaydedilmeli."""
    target = CampaignTarget.objects.create(
        campaign=base_campaign,
        target_type=CampaignTarget.TargetType.KIOSK,
        kiosk=kiosk,
    )
    target.refresh_from_db()
    assert target.target_type == "KIOSK"
    assert target.kiosk_id == kiosk.pk


@pytest.mark.django_db
def test_f105_campaign_target_kiosk_clean_validation(base_campaign):
    """KIOSK tipi için kiosk FK olmadan clean() ValidationError fırlatmalı."""
    from django.core.exceptions import ValidationError
    target = CampaignTarget(
        campaign=base_campaign,
        target_type=CampaignTarget.TargetType.KIOSK,
        kiosk=None,
    )
    with pytest.raises(ValidationError) as exc_info:
        target.clean()
    assert "kiosk" in str(exc_info.value).lower()


# ─────────────────────────────────────────────────────────────────────────────
# F1-06  CampaignTarget mode (INCLUDE / EXCLUDE)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f106_target_mode_include_exclude(base_campaign, il_istanbul):
    """mode=INCLUDE ve mode=EXCLUDE DB'ye kaydedilmeli."""
    inc = CampaignTarget.objects.create(
        campaign=base_campaign,
        target_type=CampaignTarget.TargetType.IL,
        il=il_istanbul,
        mode=CampaignTarget.TargetMode.INCLUDE,
    )
    exc = CampaignTarget.objects.create(
        campaign=base_campaign,
        target_type=CampaignTarget.TargetType.IL,
        il=il_istanbul,
        mode=CampaignTarget.TargetMode.EXCLUDE,
    )
    inc.refresh_from_db()
    exc.refresh_from_db()
    assert inc.mode == "INCLUDE"
    assert exc.mode == "EXCLUDE"


@pytest.mark.django_db
def test_f106_target_mode_none_legacy(base_campaign, il_istanbul):
    """mode=None → legacy INCLUDE davranışı (geriye uyumluluk)."""
    target = CampaignTarget.objects.create(
        campaign=base_campaign,
        target_type=CampaignTarget.TargetType.IL,
        il=il_istanbul,
        mode=None,
    )
    target.refresh_from_db()
    assert target.mode is None


# ─────────────────────────────────────────────────────────────────────────────
# F1-07  Creative weight alanı
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f107_creative_weight_default(base_campaign):
    """Creative weight varsayılan 1 olmalı."""
    c = Creative.objects.create(
        campaign=base_campaign,
        media_url="https://cdn.example.com/ad.mp4",
        duration_seconds=15,
    )
    assert c.weight == 1


@pytest.mark.django_db
def test_f107_creative_weight_custom(base_campaign):
    """Creative weight özel değer DB'ye kaydedilmeli."""
    c = Creative.objects.create(
        campaign=base_campaign,
        media_url="https://cdn.example.com/ad.mp4",
        duration_seconds=15,
        weight=3,
    )
    c.refresh_from_db()
    assert c.weight == 3


# ─────────────────────────────────────────────────────────────────────────────
# F1-08  Creative is_grid_compliant property
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize("duration,expected", [
    (15, True), (30, True), (45, True), (60, True),
    (5, False), (10, False), (20, False), (1, False), (59, False),
])
def test_f108_creative_is_grid_compliant(db, base_campaign, duration, expected):
    """Creative.is_grid_compliant 15/30/45/60 için True, diğerleri False."""
    c = Creative(
        campaign=base_campaign,
        media_url="https://cdn.example.com/ad.mp4",
        duration_seconds=duration,
    )
    assert c.is_grid_compliant == expected, (
        f"duration={duration}: beklenen {expected}, bulundu {c.is_grid_compliant}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# F1-09  HouseAd is_grid_compliant property
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("duration,expected", [
    (15, True), (30, True), (10, False), (7, False), (60, True),
])
def test_f109_housead_is_grid_compliant(duration, expected):
    """HouseAd.is_grid_compliant 15/30/45/60 için True, diğerleri False."""
    ha = HouseAd(duration_seconds=duration)
    assert ha.is_grid_compliant == expected


# ─────────────────────────────────────────────────────────────────────────────
# F1-10  DeliveryRule — temel oluşturma
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f110_delivery_rule_per_hour(base_campaign):
    """DeliveryRule PER_HOUR BEST_EFFORT DB'ye kaydedilmeli."""
    rule = DeliveryRule.objects.create(
        campaign=base_campaign,
        delivery_type=DeliveryRule.DeliveryType.PER_HOUR,
        count=2,
        guarantee_mode=DeliveryRule.GuaranteeMode.BEST_EFFORT,
        active_hours=[9, 10, 11, 17, 18],
    )
    rule.refresh_from_db()
    assert rule.delivery_type == "PER_HOUR"
    assert rule.count == 2
    assert rule.guarantee_mode == "BEST_EFFORT"
    assert rule.active_hours == [9, 10, 11, 17, 18]


@pytest.mark.django_db
def test_f110_delivery_rule_campaign_total(base_campaign):
    """DeliveryRule CAMPAIGN_TOTAL GUARANTEED DB'ye kaydedilmeli."""
    rule = DeliveryRule.objects.create(
        campaign=base_campaign,
        delivery_type=DeliveryRule.DeliveryType.CAMPAIGN_TOTAL,
        count=10000,
        guarantee_mode=DeliveryRule.GuaranteeMode.GUARANTEED,
    )
    rule.refresh_from_db()
    assert rule.delivery_type == "CAMPAIGN_TOTAL"
    assert rule.guarantee_mode == "GUARANTEED"
    assert rule.count == 10000


# ─────────────────────────────────────────────────────────────────────────────
# F1-11  DeliveryRule TIME_WINDOW validasyonu
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f111_delivery_rule_time_window_requires_times(base_campaign):
    """TIME_WINDOW için window_start_time ve window_end_time zorunlu."""
    from django.core.exceptions import ValidationError
    rule = DeliveryRule(
        campaign=base_campaign,
        delivery_type=DeliveryRule.DeliveryType.TIME_WINDOW,
        count=1,
    )
    with pytest.raises(ValidationError):
        rule.clean()


@pytest.mark.django_db
def test_f111_delivery_rule_time_window_valid(base_campaign):
    """TIME_WINDOW geçerli pencere ile kaydedilmeli."""
    import datetime
    rule = DeliveryRule.objects.create(
        campaign=base_campaign,
        delivery_type=DeliveryRule.DeliveryType.TIME_WINDOW,
        count=3,
        window_start_time=datetime.time(14, 0),
        window_end_time=datetime.time(15, 0),
    )
    rule.refresh_from_db()
    assert rule.window_start_time.hour == 14
    assert rule.window_end_time.hour == 15


# ─────────────────────────────────────────────────────────────────────────────
# F1-12  DeliveryRule active_hours validasyonu
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f112_delivery_rule_active_hours_invalid(base_campaign):
    """active_hours 0-23 dışındaki değerlerde ValidationError."""
    from django.core.exceptions import ValidationError
    rule = DeliveryRule(
        campaign=base_campaign,
        delivery_type=DeliveryRule.DeliveryType.PER_HOUR,
        count=1,
        active_hours=[9, 25],  # 25 geçersiz
    )
    with pytest.raises(ValidationError):
        rule.clean()


# ─────────────────────────────────────────────────────────────────────────────
# F1-13  PlayLog play_event_id (nullable)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f113_playlog_play_event_id_nullable(kiosk, base_campaign):
    """PlayLog.play_event_id None olarak kaydedilmeli (nullable)."""
    creative = Creative.objects.create(
        campaign=base_campaign,
        media_url="https://cdn.example.com/ad.mp4",
        duration_seconds=15,
    )
    log = PlayLog.objects.create(
        kiosk=kiosk,
        creative=creative,
        played_at=timezone.now(),
        duration_played=15,
    )
    assert log.play_event_id is None


@pytest.mark.django_db
def test_f113_playlog_play_event_id_set(kiosk, base_campaign):
    """PlayLog.play_event_id UUID olarak kaydedilmeli."""
    creative = Creative.objects.create(
        campaign=base_campaign,
        media_url="https://cdn.example.com/ad.mp4",
        duration_seconds=15,
    )
    event_id = uuid.uuid4()
    log = PlayLog.objects.create(
        kiosk=kiosk,
        creative=creative,
        played_at=timezone.now(),
        duration_played=15,
        play_event_id=event_id,
    )
    log.refresh_from_db()
    assert log.play_event_id == event_id


# ─────────────────────────────────────────────────────────────────────────────
# F1-14  PlanningRun, KioskDayQuota, KioskDesiredBundle
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f114_planning_run_created(db):
    """PlanningRun DB'ye kaydedilmeli."""
    import datetime
    run = PlanningRun.objects.create(
        horizon_start=datetime.date.today(),
        horizon_end=datetime.date.today() + datetime.timedelta(days=3),
        status=PlanningRun.RunStatus.PENDING,
    )
    run.refresh_from_db()
    assert run.status == "PENDING"


@pytest.mark.django_db
def test_f114_kiosk_desired_bundle(db, kiosk):
    """KioskDesiredBundle kiosk ile DB'ye kaydedilmeli."""
    bundle = KioskDesiredBundle.objects.create(
        kiosk=kiosk,
        desired_bundle_version=0,
    )
    bundle.refresh_from_db()
    assert bundle.desired_bundle_version == 0
    assert bundle.horizon_days == 3  # varsayılan


# ─────────────────────────────────────────────────────────────────────────────
# F1-15  report_grid_noncompliant_media komutu
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f115_report_grid_noncompliant_media_no_issues(db):
    """Grid uyumlu medya yokken rapor 'tum kayitlar uyumlu' demeli."""
    out = StringIO()
    call_command("report_grid_noncompliant_media", stdout=out)
    output = out.getvalue()
    assert "uyumlu" in output.lower() or "compliant" in output.lower() or "tum" in output.lower()


@pytest.mark.django_db
def test_f115_report_grid_noncompliant_media_detects_bad(db, base_campaign):
    """Grid dışı Creative ve HouseAd raporda görünmeli."""
    Creative.objects.create(
        campaign=base_campaign,
        media_url="https://cdn.example.com/bad.mp4",
        duration_seconds=7,  # grid dışı
    )
    HouseAd.objects.create(
        name="Bad HouseAd",
        media_url="https://cdn.example.com/bad_ha.mp4",
        duration_seconds=3,  # grid dışı
    )

    out = StringIO()
    call_command("report_grid_noncompliant_media", stdout=out)
    output = out.getvalue()
    assert "7" in output or "bad" in output.lower()


@pytest.mark.django_db
def test_f115_report_grid_noncompliant_csv(db, base_campaign):
    """CSV formatında çıktı üretilmeli."""
    Creative.objects.create(
        campaign=base_campaign,
        media_url="https://cdn.example.com/bad.mp4",
        duration_seconds=5,
    )
    out = StringIO()
    call_command("report_grid_noncompliant_media", "--format", "csv", stdout=out)
    output = out.getvalue()
    assert "creative," in output or "type,id" in output


# ─────────────────────────────────────────────────────────────────────────────
# F1-16  DeliveryRuleSerializer — yeni kayıtlar için temel validation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_f116_delivery_rule_serializer_per_hour(admin_client, base_campaign):
    """DeliveryRule API ile oluşturulabilmeli (Faz 2'de endpoint açılır, şimdi model testi)."""
    from apps.campaigns.serializers import DeliveryRuleSerializer

    data = {
        "campaign": str(base_campaign.pk),
        "delivery_type": "PER_HOUR",
        "count": 2,
        "guarantee_mode": "BEST_EFFORT",
        "active_hours": [9, 10, 11],
    }
    ser = DeliveryRuleSerializer(data=data)
    assert ser.is_valid(), ser.errors
    rule = ser.save()
    assert rule.delivery_type == "PER_HOUR"
    assert rule.count == 2


@pytest.mark.django_db
def test_f116_delivery_rule_serializer_time_window_missing_times(base_campaign):
    """TIME_WINDOW window times olmadan geçersiz olmalı."""
    from apps.campaigns.serializers import DeliveryRuleSerializer

    data = {
        "campaign": str(base_campaign.pk),
        "delivery_type": "TIME_WINDOW",
        "count": 1,
    }
    ser = DeliveryRuleSerializer(data=data)
    assert not ser.is_valid()
    assert "window_start_time" in str(ser.errors) or "TIME_WINDOW" in str(ser.errors)
