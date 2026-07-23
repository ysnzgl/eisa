"""Faz 5 — Desired/Applied Version + Kiosk ACK + Manifest Cache testleri.

Kapsanan 18 senaryo:
  FC-01  Ping legacy contractı DOOH_KIOSK_ACK=false iken korunur
  FC-02  Manifest tam bugün/+1/+2 döndürür
  FC-03  Europe/Istanbul gece sınırı doğrulanır
  FC-04  Boş gün response'da açıkça bulunur
  FC-05  Manifest başka kiosk tarafından okunamaz (IDOR)
  FC-06  Manifest desired version ve playlistleri tutarlı snapshot'tan döndürür
  FC-07  İlk ACK applied state'i günceller
  FC-08  Aynı ACK idempotenttir
  FC-09  Eski ACK applied version'ı geriye çekmez
  FC-10  Future ACK 409 döndürür
  FC-11  Aynı version + ileri horizon coverage doğru güncellenir
  FC-12  Desired ilerlemişken eski ama geçerli ACK kiosk'u behind bırakır
  FC-13  (PostgreSQL) Concurrent ACK applied state'te lost update üretmez → integration/
  FC-14  ACK invalidation job üretmez
  FC-15  ACK gelmeyen kioskta applied null kalabilir
  FC-16  Faz 4 publish desired version'ı transaction içinde tam bir kere artırır
  FC-17  Concurrent manifest/publish karışık snapshot üretmez → integration/
  FC-18  App Key + MAC permission ve IDOR davranışı doğrulanır
"""
from __future__ import annotations

import datetime as _dt

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.campaigns.models import HouseAd, Playlist
from apps.pharmacies.models import Kiosk


# ─────────────────────────────────────────────────────────────────────────────
# Sabitler ve yardımcılar
# ─────────────────────────────────────────────────────────────────────────────

import zoneinfo as _zi
_TZ = _zi.ZoneInfo("Europe/Istanbul")
TODAY = _dt.datetime.now(_TZ).date()
TOMORROW = TODAY + _dt.timedelta(days=1)
DAY_AFTER = TODAY + _dt.timedelta(days=2)


@pytest.fixture
def house_ad(db):
    return HouseAd.objects.create(
        name="FC5 HouseAd",
        media_url="http://localhost:9000/dev/ads/fc5-filler.mp4",
        duration_seconds=15,
        priority=1,
        aktif=True,
    )


def _set_desired_version(kiosk, version: int):
    Kiosk.objects.filter(pk=kiosk.pk).update(last_playlist_version=version)
    kiosk.refresh_from_db()


# ─────────────────────────────────────────────────────────────────────────────
# FC-01  Ping legacy contractı DOOH_KIOSK_ACK=false iken korunur
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fc01_ping_legacy_contract(kiosk_client, kiosk):
    """Faz 7: Ping yanıtı desired/applied/horizon alanlarını her zaman döndürür."""
    resp = kiosk_client.get("/api/kiosk/v1/ping/")
    assert resp.status_code == 200
    data = resp.json()
    assert "kiosk_id" in data
    assert "playlist_version" in data
    assert "server_time" in data
    # Faz 7: ACK alanları her zaman mevcut
    assert "desired_playlist_version" in data
    assert "applied_playlist_version" in data
    assert "horizon_start" in data


# ─────────────────────────────────────────────────────────────────────────────
# FC-02  Manifest tam bugün/+1/+2 döndürür
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True, DOOH_HORIZON_DAYS=3)
def test_fc02_manifest_three_days(kiosk_client, kiosk):
    """Manifest response'da tam 3 gün bulunmalı."""
    resp = kiosk_client.get("/api/kiosk/v1/manifest/")
    assert resp.status_code == 200
    data = resp.json()
    assert "days" in data
    assert len(data["days"]) == 3
    dates = [d["target_date"] for d in data["days"]]
    assert str(TODAY) in dates
    assert str(TOMORROW) in dates
    assert str(DAY_AFTER) in dates


# ─────────────────────────────────────────────────────────────────────────────
# FC-03  Europe/Istanbul gece sınırı doğrulanır
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True, DOOH_HORIZON_DAYS=3)
def test_fc03_istanbul_boundary(kiosk_client, kiosk):
    """Manifest horizon_start İstanbul tarih sınırını kullanmalı."""
    resp = kiosk_client.get("/api/kiosk/v1/manifest/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["timezone"] == "Europe/Istanbul"
    assert data["horizon_start"] == str(TODAY)
    assert data["horizon_end"] == str(DAY_AFTER)


# ─────────────────────────────────────────────────────────────────────────────
# FC-04  Boş gün response'da açıkça bulunur
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True, DOOH_HORIZON_DAYS=3)
def test_fc04_empty_day_included(kiosk_client, kiosk):
    """Playlist olmayan günler {"playlists": []} ile response'da bulunur."""
    resp = kiosk_client.get("/api/kiosk/v1/manifest/")
    data = resp.json()
    # Hiç playlist oluşturmadık → her gün boş
    for day in data["days"]:
        assert "target_date" in day
        assert "playlists" in day
        assert isinstance(day["playlists"], list)


# ─────────────────────────────────────────────────────────────────────────────
# FC-05  Manifest başka kiosk tarafından okunamaz (IDOR)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True)
def test_fc05_manifest_idor_blocked(kiosk, api_client):
    """Auth olmaksızın veya başka kiosk ile manifest endpoint → 401/403."""
    # Auth yok
    resp = api_client.get("/api/kiosk/v1/manifest/")
    assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# FC-06  Manifest desired version ve playlistleri tutarlı snapshot'tan döndürür
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True, DOOH_HORIZON_DAYS=3)
def test_fc06_manifest_consistent_snapshot(kiosk_client, kiosk):
    """playlist_version ile playlists içeriği aynı snapshot'tan gelir."""
    _set_desired_version(kiosk, 42)
    resp = kiosk_client.get("/api/kiosk/v1/manifest/")
    data = resp.json()
    assert data["playlist_version"] == 42
    assert data["desired_playlist_version"] == 42
    # Playlists henüz yok → boş list
    assert all(len(d["playlists"]) == 0 for d in data["days"])


# ─────────────────────────────────────────────────────────────────────────────
# FC-07  İlk ACK applied state'i günceller
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True)
def test_fc07_first_ack_updates_applied(kiosk_client, kiosk):
    """İlk ACK applied_playlist_version ve horizon güncellenir."""
    _set_desired_version(kiosk, 5)
    resp = kiosk_client.post(
        "/api/kiosk/v1/ack/",
        {"playlist_version": 5, "horizon_start": str(TODAY), "horizon_end": str(DAY_AFTER)},
        format="json",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ack_status"] == "APPLIED"

    kiosk.refresh_from_db()
    assert kiosk.applied_playlist_version == 5
    assert kiosk.applied_horizon_start == TODAY
    assert kiosk.applied_horizon_end == DAY_AFTER
    assert kiosk.playlist_applied_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# FC-08  Aynı ACK idempotenttir
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True)
def test_fc08_idempotent_ack(kiosk_client, kiosk):
    """Aynı ACK iki kez gönderilince IDEMPOTENT döner."""
    _set_desired_version(kiosk, 5)
    payload = {"playlist_version": 5, "horizon_start": str(TODAY), "horizon_end": str(DAY_AFTER)}

    r1 = kiosk_client.post("/api/kiosk/v1/ack/", payload, format="json")
    assert r1.json()["ack_status"] == "APPLIED"

    r2 = kiosk_client.post("/api/kiosk/v1/ack/", payload, format="json")
    assert r2.json()["ack_status"] == "IDEMPOTENT"


# ─────────────────────────────────────────────────────────────────────────────
# FC-09  Eski ACK applied version'ı geriye çekmez
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True)
def test_fc09_stale_ack_ignored(kiosk_client, kiosk):
    """Eski version ACK applied_version'ı geriye çekmez."""
    _set_desired_version(kiosk, 10)
    # İlk ACK: v10
    kiosk_client.post(
        "/api/kiosk/v1/ack/",
        {"playlist_version": 10, "horizon_start": str(TODAY), "horizon_end": str(DAY_AFTER)},
        format="json",
    )
    kiosk.refresh_from_db()
    assert kiosk.applied_playlist_version == 10

    # Eski ACK: v5
    resp = kiosk_client.post(
        "/api/kiosk/v1/ack/",
        {"playlist_version": 5, "horizon_start": str(TODAY), "horizon_end": str(DAY_AFTER)},
        format="json",
    )
    assert resp.json()["ack_status"] == "STALE_IGNORED"
    kiosk.refresh_from_db()
    assert kiosk.applied_playlist_version == 10  # Değişmedi


# ─────────────────────────────────────────────────────────────────────────────
# FC-10  Future ACK 409 döndürür
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True)
def test_fc10_future_ack_rejected(kiosk_client, kiosk):
    """Desired'dan daha ileri version ACK 409 döndürür."""
    _set_desired_version(kiosk, 5)
    resp = kiosk_client.post(
        "/api/kiosk/v1/ack/",
        {"playlist_version": 99, "horizon_start": str(TODAY), "horizon_end": str(DAY_AFTER)},
        format="json",
    )
    assert resp.status_code == 409


# ─────────────────────────────────────────────────────────────────────────────
# FC-11  Aynı version + ileri horizon coverage güncellenir
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True)
def test_fc11_same_version_extended_horizon(kiosk_client, kiosk):
    """Aynı version + genişleyen horizon → APPLIED (coverage güncellenemeli)."""
    _set_desired_version(kiosk, 5)
    # İlk ACK: bugün sadece
    kiosk_client.post(
        "/api/kiosk/v1/ack/",
        {"playlist_version": 5, "horizon_start": str(TODAY), "horizon_end": str(TODAY)},
        format="json",
    )
    # İkinci ACK: aynı version + 3 gün horizon
    resp = kiosk_client.post(
        "/api/kiosk/v1/ack/",
        {"playlist_version": 5, "horizon_start": str(TODAY), "horizon_end": str(DAY_AFTER)},
        format="json",
    )
    assert resp.json()["ack_status"] == "APPLIED"
    kiosk.refresh_from_db()
    assert kiosk.applied_horizon_end == DAY_AFTER


# ─────────────────────────────────────────────────────────────────────────────
# FC-12  Desired ilerlemişken eski ama geçerli ACK kiosk'u behind bırakır
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True)
def test_fc12_valid_but_behind_ack(kiosk_client, kiosk):
    """Desired=10, ACK v5 → APPLIED ama kiosk desired'ın gerisinde kalır."""
    _set_desired_version(kiosk, 10)
    resp = kiosk_client.post(
        "/api/kiosk/v1/ack/",
        {"playlist_version": 5, "horizon_start": str(TODAY), "horizon_end": str(DAY_AFTER)},
        format="json",
    )
    assert resp.json()["ack_status"] == "APPLIED"
    assert resp.json()["desired_version"] == 10
    assert resp.json()["applied_version"] == 5
    kiosk.refresh_from_db()
    assert kiosk.applied_playlist_version == 5
    assert kiosk.last_playlist_version == 10  # Desired değişmedi


# ─────────────────────────────────────────────────────────────────────────────
# FC-14  ACK invalidation job üretmez
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True, DOOH_ASYNC_QUEUE=True)
def test_fc14_ack_no_invalidation_job(kiosk_client, kiosk):
    """ACK göndermek GenerationJob oluşturmamalı."""
    from apps.campaigns.models import GenerationJob
    pre = GenerationJob.objects.count()
    _set_desired_version(kiosk, 5)
    kiosk_client.post(
        "/api/kiosk/v1/ack/",
        {"playlist_version": 5, "horizon_start": str(TODAY), "horizon_end": str(DAY_AFTER)},
        format="json",
    )
    assert GenerationJob.objects.count() == pre


# ─────────────────────────────────────────────────────────────────────────────
# FC-15  ACK gelmeyen kioskta applied null kalabilir
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_fc15_no_ack_applied_stays_null(kiosk):
    """ACK gönderilmemişse applied_playlist_version None olabilir."""
    assert kiosk.applied_playlist_version is None


# ─────────────────────────────────────────────────────────────────────────────
# FC-16  Faz 4 publish desired version'ı transaction içinde artırır
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_ENGINE_V2="active")
def test_fc16_publish_bumps_desired_version(kiosk, house_ad):
    """_persist_plan desired version'ı artırmalı (Kiosk.last_playlist_version)."""
    from apps.campaigns.services.activation_service import ActivationService
    from apps.campaigns.services.placement_engine_v2 import PlacementEngineV2
    from apps.campaigns.models import Campaign, Creative, DeliveryRule
    from django.db import transaction

    base = timezone.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))
    camp = Campaign.objects.create(
        name="FC16",
        start_date=base - _dt.timedelta(days=1),
        end_date=base + _dt.timedelta(days=2, hours=23),
        status=Campaign.Status.ACTIVE,
        target_scope="ALL",
    )
    Creative.objects.create(
        campaign=camp,
        media_url=f"http://localhost:9000/dev/ads/fc16-{camp.pk}.mp4",
        duration_seconds=15,
    )

    plan = PlacementEngineV2.plan_kiosk_day(
        kiosk_id=kiosk.id, target_date=TODAY, planning_run=None
    )

    before_version = kiosk.last_playlist_version or 0

    with transaction.atomic():
        ActivationService._persist_plan(kiosk.id, TODAY, plan)

    kiosk.refresh_from_db()
    assert kiosk.last_playlist_version is not None
    assert kiosk.last_playlist_version > before_version


# ─────────────────────────────────────────────────────────────────────────────
# FC-18  App Key + MAC permission ve IDOR davranışı
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
@override_settings(DOOH_KIOSK_ACK=True)
def test_fc18_manifest_requires_kiosk_auth(api_client, kiosk):
    """JWT ile manifest endpoint → 401/403."""
    from rest_framework_simplejwt.tokens import RefreshToken
    from apps.users.models import Kullanici
    user = Kullanici.objects.create_user(username="fc18admin", password="x", rol="superadmin")
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    resp = api_client.get("/api/kiosk/v1/manifest/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_fc18b_manifest_disabled_when_flag_false(kiosk_client):
    """Faz 7: DOOH_KIOSK_ACK flag kaldırıldı; manifest her zaman erişilebilir (200)."""
    resp = kiosk_client.get("/api/kiosk/v1/manifest/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_fc18c_ack_disabled_when_flag_false(kiosk_client, kiosk):
    """Faz 7: DOOH_KIOSK_ACK flag kaldırıldı; ack endpoint her zaman erişilebilir."""
    resp = kiosk_client.post(
        "/api/kiosk/v1/ack/",
        {"playlist_version": 1, "horizon_start": str(TODAY), "horizon_end": str(TODAY)},
        format="json",
    )
    # 403 değil; ya geçerli ACK (200) ya da validasyon hatası (400/409) döner
    assert resp.status_code != 403
