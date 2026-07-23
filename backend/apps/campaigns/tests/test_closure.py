"""Faz 0.5 + Faz 1 Kapanış Testleri.

Kapsanan senaryolar:

Faz 0.5 kapanış:
  C01  DOOH_PERSISTENT_MEDIA_URL varsayılan False (legacy mode)
  C02  Flag=True ve S3_PUBLIC_BASE_URL boşsa ImproperlyConfigured
  C03  public_url sözleşmesi: S3_PUBLIC_BASE_URL bucket dahil → media_url = base + "/" + key
  C04  _derive_object_key_from_url sadece S3_PUBLIC_BASE_URL prefix'ini strip eder
  C05  Yabancı host ve presigned URL → boş döner

Faz 1 kapanış:
  C06  target_scope: None legacy, ALL, RULES değerleri
  C07  is_guaranteed CampaignSerializer'da read-only (API üzerinden yazılamaz)
  C08  DeliveryRule canonical guarantee (GUARANTEED/BEST_EFFORT)
  C09  LEGACY_PER_LOOP API üzerinden yazılamaz
  C10  Yeni Creative API'de grid dışı süre reddedilir
  C11  Legacy Creative grid dışı süre değişmeden korunur
  C12  Yeni HouseAd API'de grid dışı süre reddedilir
  C13  A→B follows_service self-link engeli
  C14  A→B follows_service chain/depth engeli
  C15  A→B follows_service döngü engeli
  C16  A→B follows_service başarılı ilişki kurma
  C17  KioskDayQuota placed <= quota constraint
  C18  PlayLog play_event_id nullable kalıyor
  C19  Faz 0 golden-master regression
"""
from __future__ import annotations

import datetime as _dt

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.utils import timezone

from apps.campaigns.models import (
    Campaign,
    Creative,
    DeliveryRule,
    HouseAd,
    KioskDayQuota,
    PlanningRun,
    PlayLog,
)
from apps.campaigns.services.follows_service import (
    FollowsConstraintError,
    set_campaign_follows,
)


# ─────────────────────────────────────────────────────────────────────────────
# Yerel fixture'lar
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def camp(db):
    now = timezone.now()
    return Campaign.objects.create(
        name="Closure Test Camp",
        start_date=now - _dt.timedelta(days=1),
        end_date=now + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )


@pytest.fixture
def camp2(db):
    now = timezone.now()
    return Campaign.objects.create(
        name="Closure Test Camp 2",
        start_date=now - _dt.timedelta(days=1),
        end_date=now + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )


@pytest.fixture
def camp3(db):
    now = timezone.now()
    return Campaign.objects.create(
        name="Closure Test Camp 3",
        start_date=now - _dt.timedelta(days=1),
        end_date=now + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )


# ─────────────────────────────────────────────────────────────────────────────
# C01  DOOH_PERSISTENT_MEDIA_URL varsayılan False
# ─────────────────────────────────────────────────────────────────────────────


def test_c01_persistent_media_flag_default_false():
    """DOOH_PERSISTENT_MEDIA_URL varsayılan olarak False olmalı."""
    assert getattr(settings, "DOOH_PERSISTENT_MEDIA_URL", False) is False


# ─────────────────────────────────────────────────────────────────────────────
# C02  Flag=True ve S3_PUBLIC_BASE_URL boşsa ImproperlyConfigured
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(S3_PUBLIC_BASE_URL="", DOOH_PERSISTENT_MEDIA_URL=True)
def test_c02_empty_s3_public_base_raises():
    """S3_PUBLIC_BASE_URL boşken public_url() ImproperlyConfigured fırlatmalı."""
    from unittest.mock import patch
    from apps.core.services.storage_service import StorageService

    with patch.object(StorageService, "_ensure_bucket"), \
         patch("apps.core.services.storage_service.Minio"):
        StorageService._instance = None
        svc = StorageService()

    with pytest.raises(ImproperlyConfigured, match="S3_PUBLIC_BASE_URL"):
        svc.public_url("ads/test.mp4")

    # Singleton sıfırla
    StorageService._instance = None


# ─────────────────────────────────────────────────────────────────────────────
# C03  public_url sözleşmesi: media_url = S3_PUBLIC_BASE_URL + "/" + object_key
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(S3_PUBLIC_BASE_URL="https://files.eisa.com.tr/eisa-files")
def test_c03_public_url_contract():
    """S3_PUBLIC_BASE_URL bucket dahil → media_url sözleşmesi."""
    from unittest.mock import patch
    from apps.core.services.storage_service import StorageService

    with patch.object(StorageService, "_ensure_bucket"), \
         patch("apps.core.services.storage_service.Minio"):
        StorageService._instance = None
        svc = StorageService()
        url = svc.public_url("ads/abc123.mp4")

    assert url == "https://files.eisa.com.tr/eisa-files/ads/abc123.mp4"
    assert "X-Amz-" not in url
    StorageService._instance = None


# ─────────────────────────────────────────────────────────────────────────────
# C04 + C05  _derive_object_key_from_url sözleşme ve güvenlik
# ─────────────────────────────────────────────────────────────────────────────


def test_c04_derive_object_key_from_stable_url():
    """Stabil URL'den (S3_PUBLIC_BASE_URL prefix) object_key türetilmeli."""
    from apps.campaigns.serializers import _derive_object_key_from_url

    base = settings.S3_PUBLIC_BASE_URL.rstrip("/")
    stable = f"{base}/ads/abc.mp4"
    assert _derive_object_key_from_url(stable) == "ads/abc.mp4"


def test_c05_derive_object_key_rejects_foreign_host():
    """Yabancı host → boş döner."""
    from apps.campaigns.serializers import _derive_object_key_from_url

    assert _derive_object_key_from_url("https://evil.com/ads/file.mp4") == ""
    assert _derive_object_key_from_url("") == ""


def test_c05_derive_object_key_rejects_presigned():
    """Presigned URL (X-Amz-*) → boş döner."""
    from apps.campaigns.serializers import _derive_object_key_from_url

    presigned = f"{settings.S3_PUBLIC_BASE_URL}/ads/f.mp4?X-Amz-Expires=3600&X-Amz-Signature=x"
    assert _derive_object_key_from_url(presigned) == ""


def test_c05_derive_object_key_rejects_path_traversal():
    """Path traversal → boş döner."""
    from apps.campaigns.serializers import _derive_object_key_from_url

    base = settings.S3_PUBLIC_BASE_URL.rstrip("/")
    traversal = f"{base}/ads/../../../etc/passwd"
    assert _derive_object_key_from_url(traversal) == ""


# ─────────────────────────────────────────────────────────────────────────────
# C06  target_scope: None=legacy, ALL, RULES
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c06_target_scope_none_is_legacy(camp):
    """Varsayılan target_scope=None → legacy davranış (hedefsiz=tüm eczaneler)."""
    assert camp.target_scope is None


@pytest.mark.django_db
def test_c06_target_scope_all_and_rules(camp):
    """target_scope ALL ve RULES DB'ye kaydedilmeli."""
    camp.target_scope = "ALL"; camp.save()
    camp.refresh_from_db()
    assert camp.target_scope == "ALL"

    camp.target_scope = "RULES"; camp.save()
    camp.refresh_from_db()
    assert camp.target_scope == "RULES"


# ─────────────────────────────────────────────────────────────────────────────
# C07  is_guaranteed CampaignSerializer'da read-only
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c07_is_guaranteed_explicit_error_on_write(admin_client):
    """is_guaranteed=True API üzerinden gönderilirse açık 400 dönmeli.

    Canonical kaynak: DeliveryRule.guarantee_mode.
    is_guaranteed artık writable değil; True gönderilirse 400 üret.
    """
    now = timezone.now()
    r = admin_client.post(
        "/api/campaigns/v2/campaigns/",
        {
            "name": "C07 Campaign",
            "start_date": now.isoformat(),
            "end_date": (now + _dt.timedelta(days=10)).isoformat(),
            "status": "ACTIVE",
            "target_scope": "ALL",
            "is_guaranteed": True,  # Canonical değil → 400
        },
        format="json",
    )
    assert r.status_code == 400, (
        f"is_guaranteed=True gönderilince 400 bekleniyor, bulundu {r.status_code}"
    )
    assert "is_guaranteed" in str(r.content), "Hata mesajı is_guaranteed içermeli"


# ─────────────────────────────────────────────────────────────────────────────
# C08  DeliveryRule canonical guarantee
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c08_delivery_rule_canonical_guarantee(camp):
    """DeliveryRule.guarantee_mode canonical garanti kaynağı olmalı."""
    rule = DeliveryRule.objects.create(
        campaign=camp,
        delivery_type=DeliveryRule.DeliveryType.PER_HOUR,
        count=2,
        guarantee_mode=DeliveryRule.GuaranteeMode.GUARANTEED,
    )
    rule.refresh_from_db()
    assert rule.guarantee_mode == "GUARANTEED"
    # Faz 7: Campaign.is_guaranteed field kaldırıldı; canonical kaynak DeliveryRule.


# ─────────────────────────────────────────────────────────────────────────────
# C09  LEGACY_PER_LOOP API üzerinden yazılamaz
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c09_legacy_per_loop_rejected_via_serializer(camp):
    """LEGACY_PER_LOOP DeliveryRuleSerializer üzerinden yazılamaz."""
    from apps.campaigns.serializers import DeliveryRuleSerializer

    data = {
        "campaign": str(camp.pk),
        "delivery_type": "LEGACY_PER_LOOP",
        "count": 1,
    }
    ser = DeliveryRuleSerializer(data=data)
    assert not ser.is_valid()
    assert "LEGACY_PER_LOOP" in str(ser.errors)


# ─────────────────────────────────────────────────────────────────────────────
# C10  Yeni Creative API'de grid dışı süre reddedilir
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c10_new_creative_grid_invalid_via_api(admin_client, camp):
    """API üzerinden yeni Creative'de grid dışı süre (örn. 7s) reddedilmeli."""
    stable = f"{settings.S3_PUBLIC_BASE_URL}/ads/test.mp4"
    r = admin_client.post(
        "/api/campaigns/v2/creatives/",
        {"campaign": str(camp.pk), "media_url": stable, "duration_seconds": 7},
        format="json",
    )
    assert r.status_code == 400, f"7s grid-dışı yeni creative kabul edilmemeli. Status={r.status_code}"
    assert "grid" in str(r.content).lower() or "15" in str(r.content)


@pytest.mark.parametrize("valid_dur", [15, 30, 45, 60])
@pytest.mark.django_db
def test_c10_new_creative_grid_valid_via_api(admin_client, camp, valid_dur):
    """API üzerinden yeni Creative'de {15,30,45,60} kabul edilmeli."""
    stable = f"{settings.S3_PUBLIC_BASE_URL}/ads/test_{valid_dur}.mp4"
    r = admin_client.post(
        "/api/campaigns/v2/creatives/",
        {"campaign": str(camp.pk), "media_url": stable, "duration_seconds": valid_dur},
        format="json",
    )
    assert r.status_code == 201, f"{valid_dur}s kabul edilmeli. Response={r.content}"


# ─────────────────────────────────────────────────────────────────────────────
# C11  Legacy Creative grid dışı süre değişmeden korunur
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c11_legacy_creative_unchanged_duration_preserved(admin_client, camp):
    """Legacy Creative (7s) aynı süreyle PATCH'lenirse kabul edilmeli."""
    # ORM ile grid-dışı legacy kayıt oluştur
    creative = Creative.objects.create(
        campaign=camp,
        media_url="https://cdn.example.com/legacy.mp4",
        duration_seconds=7,  # grid-dışı legacy
    )
    # Aynı süreyle PATCH → korunmalı (legacy compat)
    r = admin_client.patch(
        f"/api/campaigns/v2/creatives/{creative.pk}/",
        {"duration_seconds": 7, "name": "Updated Name"},
        format="json",
    )
    assert r.status_code == 200, (
        f"Legacy creative ayni sure ile guncellenmeli. Response={r.content}"
    )

    # Farklı grid-dışı süre → reddedilmeli
    r2 = admin_client.patch(
        f"/api/campaigns/v2/creatives/{creative.pk}/",
        {"duration_seconds": 3},
        format="json",
    )
    assert r2.status_code == 400, "Yeni grid-disi sure degisimi reddedilmeli"


# ─────────────────────────────────────────────────────────────────────────────
# C12  Yeni HouseAd API'de grid dışı süre reddedilir
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c12_new_housead_grid_invalid_via_api(admin_client):
    """API üzerinden yeni HouseAd'de grid dışı süre (örn. 3s) reddedilmeli."""
    stable = f"{settings.S3_PUBLIC_BASE_URL}/ads/housead.mp4"
    r = admin_client.post(
        "/api/campaigns/v2/house-ads/",
        {"name": "Bad HouseAd", "media_url": stable, "duration_seconds": 3},
        format="json",
    )
    assert r.status_code == 400, f"3s grid-dışı housead kabul edilmemeli. Status={r.status_code}"


# ─────────────────────────────────────────────────────────────────────────────
# C13–C16  A→B follows_service
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c13_follows_service_self_link_rejected(camp):
    """set_campaign_follows: self-link FollowsConstraintError fırlatmalı."""
    with pytest.raises(FollowsConstraintError, match="self-link"):
        set_campaign_follows(str(camp.pk), str(camp.pk))


@pytest.mark.django_db
def test_c14_follows_service_chain_rejected(camp, camp2, camp3):
    """A → B → C zinciri reddedilmeli."""
    # B, A'yı takip ediyor
    set_campaign_follows(str(camp2.pk), str(camp.pk))
    camp2.refresh_from_db()
    assert camp2.follows_id == camp.pk

    # C, B'yi takip etmeye çalışıyor → B.follows=A (zincir)
    with pytest.raises(FollowsConstraintError):
        set_campaign_follows(str(camp3.pk), str(camp2.pk))


@pytest.mark.django_db
def test_c15_follows_service_cycle_rejected(camp, camp2):
    """A → B ve B → A döngüsü reddedilmeli."""
    set_campaign_follows(str(camp.pk), str(camp2.pk))
    camp.refresh_from_db()
    assert camp.follows_id == camp2.pk

    # B → A döngüsü
    with pytest.raises(FollowsConstraintError):  # Dongu/cycle mesajı içermeli
        set_campaign_follows(str(camp2.pk), str(camp.pk))


@pytest.mark.django_db
def test_c16_follows_service_valid_link(camp, camp2):
    """A → B geçerli ilişki kurulmalı."""
    result = set_campaign_follows(str(camp.pk), str(camp2.pk))
    result.refresh_from_db()
    assert result.follows_id == camp2.pk

    # Clear
    result2 = set_campaign_follows(str(camp.pk), None)
    result2.refresh_from_db()
    assert result2.follows_id is None


# ─────────────────────────────────────────────────────────────────────────────
# C17  KioskDayQuota placed <= quota DB constraint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c17_kiosk_day_quota_placed_lte_quota(kiosk, camp):
    """placed > quota DB constraint ihlali → IntegrityError/ValidationError."""
    import datetime
    from django.db import IntegrityError

    run = PlanningRun.objects.create(
        horizon_start=datetime.date.today(),
        horizon_end=datetime.date.today() + datetime.timedelta(days=3),
    )
    # Geçerli kayıt
    quota = KioskDayQuota.objects.create(
        planning_run=run,
        campaign=camp,
        kiosk=kiosk,
        date=datetime.date.today(),
        quota=10,
        placed=5,
    )
    quota.refresh_from_db()
    assert quota.placed == 5

    # placed > quota → constraint ihlali
    with pytest.raises(IntegrityError):
        KioskDayQuota.objects.create(
            planning_run=run,
            campaign=camp,
            kiosk=kiosk,
            date=datetime.date.today() + datetime.timedelta(days=1),
            quota=5,
            placed=10,  # > quota
        )


# ─────────────────────────────────────────────────────────────────────────────
# C18  PlayLog play_event_id nullable
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c18_playlog_play_event_id_nullable(kiosk, camp):
    """PlayLog.play_event_id nullable olmalı (K5 staged migration)."""
    creative = Creative.objects.create(
        campaign=camp,
        media_url="https://cdn.example.com/ad.mp4",
        duration_seconds=15,
    )
    log = PlayLog.objects.create(
        kiosk=kiosk,
        creative=creative,
        played_at=timezone.now(),
        duration_played=15,
        # play_event_id belirtilmedi → NULL
    )
    assert log.play_event_id is None


# ─────────────────────────────────────────────────────────────────────────────
# C19  Golden-master regression (Faz 0 testlerinin kırılmadığı)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_c19_golden_master_m08_target_unchanged(kiosk, camp):
    """Hedefsiz kampanya (target_scope=None, CampaignTarget yok) → tüm kiosklar.

    Bu golden-master davranışı korunmalı (test_gm_no_target_means_all_current gibi).
    """
    from apps.campaigns.services.scheduler import PlaylistGenerator
    import datetime

    from apps.campaigns.models import ScheduleRule, HouseAd

    HouseAd.objects.create(
        name="filler",
        media_url="https://cdn.example.com/f.mp4",
        duration_seconds=15,
        aktif=True,
    )
    Creative.objects.create(
        campaign=camp,
        media_url="https://cdn.example.com/ad.mp4",
        duration_seconds=15,
    )
    ScheduleRule.objects.create(
        campaign=camp,
        frequency_type=ScheduleRule.FrequencyType.PER_HOUR,
        frequency_value=1,
    )

    # Tarihin camp.start_date ve camp.end_date arasında OLDUĞU bir gün seç.
    # camp fixture: start_date = now-1gün, end_date = now+30gün
    # camp'in start_date'ini gece yarısına sabitle (noon filtresini geçmesi için)
    camp.start_date = timezone.now() - _dt.timedelta(days=2)
    camp.save(update_fields=["start_date"])

    today = datetime.date.today() - datetime.timedelta(days=1)
    playlists = PlaylistGenerator(kiosk, today).generate()
    assert len(playlists) == 24, "24 saatlik playlist uretilmeli"

    pl0 = next(p for p in playlists if p.target_hour == 0)
    creative_items = [i for i in pl0.items.all() if i.creative_id]
    assert len(creative_items) >= 1, "Hedefsiz kampanya bu kioskta gorunmeli"


# 
# Faz 7  Deprecated Campaign alanlar (C20-C25)
# 

@pytest.mark.django_db
def test_c20_is_guaranteed_any_value_returns_400(admin_client):
    """Faz 7: is_guaranteed herhangi degerde (True, False, null) gonderilinince 400 donmeli."""
    now = timezone.now()
    base = {
        "name": "C20", "start_date": now.isoformat(),
        "end_date": (now + _dt.timedelta(days=5)).isoformat(),
        "status": "ACTIVE", "target_scope": "ALL",
    }
    for val in [True, False, None, 0]:
        r = admin_client.post("/api/campaigns/v2/campaigns/", {**base, "is_guaranteed": val}, format="json")
        assert r.status_code == 400, f"is_guaranteed={val} icin 400 bekleniyor, {r.status_code} alindi"
        assert "is_guaranteed" in str(r.content)


@pytest.mark.django_db
def test_c21_impression_goal_any_value_returns_400(admin_client):
    """Faz 7: impression_goal herhangi degerde gonderilinince 400 donmeli."""
    now = timezone.now()
    base = {
        "name": "C21", "start_date": now.isoformat(),
        "end_date": (now + _dt.timedelta(days=5)).isoformat(),
        "status": "ACTIVE", "target_scope": "ALL",
    }
    for val in [1000, 0, None]:
        r = admin_client.post("/api/campaigns/v2/campaigns/", {**base, "impression_goal": val}, format="json")
        assert r.status_code == 400, f"impression_goal={val} icin 400 bekleniyor, {r.status_code} alindi"
        assert "impression_goal" in str(r.content)


@pytest.mark.django_db
def test_c22_frequency_cap_any_value_returns_400(admin_client):
    """Faz 7: frequency_cap_per_hour herhangi degerde gonderilinince 400 donmeli."""
    now = timezone.now()
    base = {
        "name": "C22", "start_date": now.isoformat(),
        "end_date": (now + _dt.timedelta(days=5)).isoformat(),
        "status": "ACTIVE", "target_scope": "ALL",
    }
    for val in [5, 0, None]:
        r = admin_client.post("/api/campaigns/v2/campaigns/", {**base, "frequency_cap_per_hour": val}, format="json")
        assert r.status_code == 400, f"frequency_cap_per_hour={val} icin 400 bekleniyor, {r.status_code} alindi"
        assert "frequency_cap_per_hour" in str(r.content)


@pytest.mark.django_db
def test_c23_deprecated_fields_not_in_response(admin_client):
    """Faz 7: Guncel campaign response deprecated alanlar icermemeli."""
    now = timezone.now()
    r = admin_client.post(
        "/api/campaigns/v2/campaigns/",
        {
            "name": "C23", "start_date": now.isoformat(),
            "end_date": (now + _dt.timedelta(days=5)).isoformat(),
            "status": "ACTIVE", "target_scope": "ALL",
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    body = r.json()
    assert "is_guaranteed" not in body
    assert "impression_goal" not in body
    assert "frequency_cap_per_hour" not in body
    assert "target_pharmacies" not in body


@pytest.mark.django_db
def test_c24_campaign_without_deprecated_fields_ok(admin_client):
    """Faz 7: Deprecated alan gondermeden kampanya olusturulabilmeli."""
    now = timezone.now()
    r = admin_client.post(
        "/api/campaigns/v2/campaigns/",
        {
            "name": "C24", "start_date": now.isoformat(),
            "end_date": (now + _dt.timedelta(days=5)).isoformat(),
            "status": "ACTIVE", "target_scope": "ALL",
        },
        format="json",
    )
    assert r.status_code == 201, r.content


@pytest.mark.django_db
def test_c25_migration_0020_fields_absent_from_model():
    """Faz 7: Migration 0020 sonrasi deprecated alanlar Campaign modelinde bulunmamali."""
    from apps.campaigns.models import Campaign
    field_names = [f.name for f in Campaign._meta.get_fields()]
    for f in ["is_guaranteed", "impression_goal", "frequency_cap_per_hour"]:
        assert f not in field_names, f"{f} Campaign modelinde hala mevcut  migration 0020 uygulanmali"
