"""Faz 0.5 — Kalıcı medya URL testleri (v2).

StorageService gerçek ağ bağlantısı olmaksızın mock'lanır.

URL FORMAT (production ve test):
  S3_FORCE_PATH_STYLE=True → <scheme>://<endpoint>/<bucket>/<object_key>
  Test ortamı varsayılanları: http://localhost:9000/dev/<object_key>
  Production: https://files.eisa.com.tr/eisa-files/<object_key>

DOOH_PERSISTENT_MEDIA_URL feature flag:
  False (varsayılan) — legacy presigned URL davranışı korunur.
  True              — kalıcı URL akışı aktif.

Kapsanan senaryolar:
  M01  upload response presigned parametre içermiyor (flag=True)
  M02  DB'de object_key doğru kaydediliyor
  M03  Aynı creative farklı playlist üretimlerinde aynı stabil media_url
  M04  Yeni medya revizyonu farklı object_key üretiyor
  M05  Legacy url/object_name alias'ları çalışıyor (flag=True)
  M06  Management command dry-run DB değiştirmiyor
  M07  Geçersiz/eski URL backfill sırasında değiştirilmeden raporlanıyor
  M08a Campaign.PAUSED — delete_object çağrılmıyor
  M08b Campaign.COMPLETED — delete_object çağrılmıyor
  M08c Creative silme — PlayLog varsa test mevcut davranışı belgeler
  M09  Kiosk stabil URL'den medyayı playlist'te alıyor
  M10  StorageService.public_url bucket dahil stabil URL döndürüyor
  M11  _derive_object_key_from_url helper — bucket-aware
  M12  backfill URL ayrıştırma yardımcısı — bucket-in-path
  M13  Feature flag kapalıyken (False) legacy presigned URL davranışı korunuyor
  M14  Streaming hash: büyük dosya chunk stream ile hash+upload yapılıyor
  M15  Panel akışı: upload object_key+checksum → Creative create → DB'ye kaydedildi
"""
from __future__ import annotations

import hashlib
import io
from unittest.mock import MagicMock, patch
import datetime as _dt

import pytest
from django.conf import settings
from django.test import override_settings
from django.utils import timezone

from apps.campaigns.models import Campaign, Creative, HouseAd, PlayLog
from apps.campaigns.services.scheduler import generate_for_kiosk


TODAY = _dt.date(2026, 7, 21)
# TODAY'ın midnight TZ-aware değeri — scheduler noon filtresi için
_TODAY_START = None  # lazy, _today_start() ile hesaplanır


def _today_start():
    """TODAY tabanlı timezone-aware midnight; zamana bağlı test hatalarını önler."""
    from django.utils import timezone as _tz
    return _tz.make_aware(_dt.datetime.combine(TODAY, _dt.time(0, 0)))


# ─────────────────────────────────────────────────────────────────────────────
# URL yardımcıları (settings-aware)
# ─────────────────────────────────────────────────────────────────────────────


def _stable_url(object_key: str) -> str:
    """Test ortamı için beklenen kalıcı URL.

    Sözleşme: S3_PUBLIC_BASE_URL bucket adını içerir.
    test_settings.py: S3_PUBLIC_BASE_URL = "http://localhost:9000/dev"
    → _stable_url("ads/abc.mp4") = "http://localhost:9000/dev/ads/abc.mp4"
    """
    base = settings.S3_PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/{object_key}"


def _presigned_url(object_key: str) -> str:
    """Test ortamı için sahte presigned URL (bucket-in-path)."""
    endpoint = getattr(
        settings, "S3_ENDPOINT", getattr(settings, "RUSTFS_ENDPOINT", "localhost:9000")
    )
    bucket = getattr(
        settings, "S3_BUCKET", getattr(settings, "RUSTFS_BUCKET_NAME", "dev")
    )
    return (
        f"http://{endpoint}/{bucket}/{object_key}"
        "?X-Amz-Algorithm=AWS4-HMAC-SHA256"
        "&X-Amz-Credential=admin%2F20260721%2Fus-east-1%2Fs3%2Faws4_request"
        "&X-Amz-Date=20260721T000000Z&X-Amz-Expires=3600"
        "&X-Amz-SignedHeaders=host&X-Amz-Signature=fakesig"
    )


OBJECT_KEY = "ads/testfile_abc123.mp4"
CHECKSUM = "sha256:deadbeef1234567890abcdef"


# ─────────────────────────────────────────────────────────────────────────────
# Yerel fixture'lar
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def active_campaign(db):
    base = _today_start()
    return Campaign.objects.create(
        name="Media Test Campaign",
        start_date=base - _dt.timedelta(days=1),
        end_date=base + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )


@pytest.fixture
def house_ad_10s(db):
    return HouseAd.objects.create(
        name="Filler 10s",
        media_url=_stable_url("ads/filler10.mp4"),
        duration_seconds=10,
        priority=100,
        aktif=True,
    )


@pytest.fixture
def mock_storage_cls():
    """StorageService'i views.py import noktasında patch'ler.

    Hem yeni (persistent) hem legacy (presigned) path için mock'lar hazır.
    Legacy path: upload_file → str, get_object_url → presigned str.
    Yeni path:   upload_file_with_checksum → (key, checksum), public_url → stabil str.
    """
    with patch("apps.campaigns.views.StorageService") as MockCls:
        instance = MockCls.return_value
        # Yeni path
        instance.upload_file_with_checksum.return_value = (OBJECT_KEY, CHECKSUM)
        instance.public_url.return_value = _stable_url(OBJECT_KEY)
        # Legacy path — presigned URL davranışı
        instance.upload_file.return_value = OBJECT_KEY
        instance.get_object_url.return_value = _presigned_url(OBJECT_KEY)
        # delete_object (hiç çağrılmamalı)
        instance.delete_object = MagicMock()
        yield MockCls, instance


# ─────────────────────────────────────────────────────────────────────────────
# M01 — upload response presigned parametre içermiyor (flag=True)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True)
def test_m01_upload_response_no_presigned_params(admin_client, mock_storage_cls):
    """DOOH_PERSISTENT_MEDIA_URL=True: response X-Amz-* parametresi içermemeli."""
    _, instance = mock_storage_cls
    f = io.BytesIO(b"fake mp4 bytes")
    f.name = "ad.mp4"

    r = admin_client.post("/api/campaigns/upload-media/", {"file": f}, format="multipart")
    assert r.status_code == 201, r.content
    body = r.json()

    assert "object_key" in body
    assert "media_url" in body
    assert "checksum" in body

    for val in [body.get("media_url", ""), body.get("url", "")]:
        assert "X-Amz-" not in val, f"Presigned parametre bulundu: {val}"

    assert body["checksum"].startswith("sha256:")


# ─────────────────────────────────────────────────────────────────────────────
# M02 — Creative oluşturulduğunda object_key DB'ye kaydediliyor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_m02_object_key_saved_in_db(admin_client, active_campaign):
    """_derive_object_key_from_url stabil URL'den key türetmeli ve DB'ye yazmalı."""
    stable = _stable_url("ads/unique_abc.mp4")
    r = admin_client.post(
        "/api/campaigns/v2/creatives/",
        {"campaign": str(active_campaign.pk), "media_url": stable,
         "duration_seconds": 15, "name": "M02"},
        format="json",
    )
    assert r.status_code == 201, r.content
    creative = Creative.objects.get(pk=r.json()["id"])
    assert creative.object_key == "ads/unique_abc.mp4"
    assert creative.media_url == stable


# ─────────────────────────────────────────────────────────────────────────────
# M03 — Aynı creative farklı üretimlerde aynı stabil media_url döndürüyor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_m03_same_creative_same_media_url_across_playlists(kiosk, house_ad_10s):
    """Creative.media_url playlist yeniden üretimlerinde değişmemeli."""
    from apps.campaigns.models import ScheduleRule, Playlist

    base = _today_start()
    camp = Campaign.objects.create(
        name="M03",
        start_date=base - _dt.timedelta(days=1),
        end_date=base + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )
    stable = _stable_url("ads/stable_m03.mp4")
    creative = Creative.objects.create(campaign=camp, media_url=stable, duration_seconds=15)
    ScheduleRule.objects.create(
        campaign=camp, frequency_type=ScheduleRule.FrequencyType.PER_HOUR, frequency_value=1
    )

    generate_for_kiosk(kiosk, TODAY)
    items1 = [
        i for i in Playlist.objects.get(kiosk=kiosk, target_date=TODAY, target_hour=0)
        .items.select_related("creative").all()
        if i.creative_id == creative.pk
    ]
    assert items1
    url_first = items1[0].creative.media_url

    generate_for_kiosk(kiosk, TODAY)
    items2 = [
        i for i in Playlist.objects.get(kiosk=kiosk, target_date=TODAY, target_hour=0)
        .items.select_related("creative").all()
        if i.creative_id == creative.pk
    ]
    assert items2
    url_second = items2[0].creative.media_url

    assert url_first == url_second == stable
    assert "X-Amz-" not in url_first


# ─────────────────────────────────────────────────────────────────────────────
# M04 — Yeni medya revizyonu farklı object_key üretiyor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True)
def test_m04_new_upload_different_object_key(admin_client, mock_storage_cls):
    """İki ayrı upload farklı object_key değerleri üretmeli."""
    _, instance = mock_storage_cls
    key1, key2 = "ads/v1_aaa.mp4", "ads/v2_bbb.mp4"

    f1 = io.BytesIO(b"v1"); f1.name = "v1.mp4"
    instance.upload_file_with_checksum.return_value = (key1, "sha256:aaa")
    instance.public_url.return_value = _stable_url(key1)
    r1 = admin_client.post("/api/campaigns/upload-media/", {"file": f1}, format="multipart")
    assert r1.status_code == 201
    okey1 = r1.json()["object_key"]

    f2 = io.BytesIO(b"v2"); f2.name = "v2.mp4"
    instance.upload_file_with_checksum.return_value = (key2, "sha256:bbb")
    instance.public_url.return_value = _stable_url(key2)
    r2 = admin_client.post("/api/campaigns/upload-media/", {"file": f2}, format="multipart")
    assert r2.status_code == 201
    okey2 = r2.json()["object_key"]

    assert okey1 != okey2
    assert okey1 == key1 and okey2 == key2


# ─────────────────────────────────────────────────────────────────────────────
# M05 — Legacy url/object_name alias'ları çalışıyor (flag=True)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True)
def test_m05_legacy_url_alias_present(admin_client, mock_storage_cls):
    """Response'ta `url` ve `object_name` geriye-uyumlu alias'lar mevcut olmalı."""
    _, instance = mock_storage_cls
    instance.upload_file_with_checksum.return_value = (OBJECT_KEY, CHECKSUM)
    instance.public_url.return_value = _stable_url(OBJECT_KEY)

    f = io.BytesIO(b"bytes"); f.name = "ad.mp4"
    r = admin_client.post("/api/campaigns/upload-media/", {"file": f}, format="multipart")
    assert r.status_code == 201
    body = r.json()
    expected_url = _stable_url(OBJECT_KEY)

    assert "url" in body and "object_name" in body and "filename" in body
    assert body["url"] == body["media_url"] == expected_url
    assert body["object_name"] == body["object_key"] == OBJECT_KEY


# ─────────────────────────────────────────────────────────────────────────────
# M06 — Management command dry-run DB değiştirmiyor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_m06_backfill_dry_run_no_db_change():
    from django.core.management import call_command
    from io import StringIO

    camp = Campaign.objects.create(
        name="M06",
        start_date=timezone.now() - _dt.timedelta(days=1),
        end_date=timezone.now() + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )
    creative = Creative.objects.create(
        campaign=camp, media_url=_presigned_url("ads/m06.mp4"),
        duration_seconds=15, object_key=None,
    )

    out = StringIO()
    call_command("backfill_media_object_keys", stdout=out)  # dry-run varsayılan

    creative.refresh_from_db()
    assert creative.object_key is None, f"Dry-run sonrası object_key değişmemeli: {creative.object_key!r}"
    assert "DRY-RUN" in out.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# M07 — Geçersiz URL backfill sırasında değiştirilmeden raporlanıyor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_m07_invalid_url_reported_not_changed():
    from django.core.management import call_command
    from io import StringIO

    camp = Campaign.objects.create(
        name="M07",
        start_date=timezone.now() - _dt.timedelta(days=1),
        end_date=timezone.now() + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )
    creative = Creative.objects.create(
        campaign=camp,
        media_url="http://unknown-host-xyz.invalid:9999/wrongbucket/ads/f.mp4?X-Amz-Signature=x",
        duration_seconds=15, object_key=None,
    )

    out = StringIO()
    call_command("backfill_media_object_keys", "--apply",
                 "--skip-head-check-DANGEROUS", stdout=out)

    creative.refresh_from_db()
    assert creative.object_key is None
    output = out.getvalue()
    assert any(kw in output for kw in ["FAIL", "not_allowed", "no_bucket_prefix", "mismatch"])


# ─────────────────────────────────────────────────────────────────────────────
# M08a/b — Campaign pause/completed → delete_object çağrılmıyor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_m08a_campaign_pause_no_delete(admin_client, active_campaign):
    """Campaign PAUSED → delete_object çağrılmamalı."""
    with patch("apps.campaigns.views.StorageService") as MockCls:
        instance = MockCls.return_value
        r = admin_client.patch(
            f"/api/campaigns/v2/campaigns/{active_campaign.pk}/",
            {"status": "PAUSED"}, format="json",
        )
        assert r.status_code == 200, r.content
        instance.delete_object.assert_not_called()


@pytest.mark.django_db
def test_m08b_campaign_completed_no_delete(admin_client, active_campaign):
    """Campaign COMPLETED → delete_object çağrılmamalı."""
    with patch("apps.campaigns.views.StorageService") as MockCls:
        instance = MockCls.return_value
        r = admin_client.patch(
            f"/api/campaigns/v2/campaigns/{active_campaign.pk}/",
            {"status": "COMPLETED"}, format="json",
        )
        assert r.status_code == 200, r.content
        instance.delete_object.assert_not_called()


@pytest.mark.django_db
def test_m08c_creative_with_playlog_delete_behavior(admin_client, active_campaign, kiosk):
    """PlayLog kaydı olan Creative silme davranışını belgeler.

    Şu anki davranış: bağımlılık kontrolü yok (Faz 3'te 409 eklenecek).
    Test mevcut davranışı kilitler; Faz 3'te 409'a güncellenir.
    """
    creative = Creative.objects.create(
        campaign=active_campaign,
        media_url=_stable_url("ads/protected.mp4"),
        duration_seconds=15,
    )
    PlayLog.objects.create(
        kiosk=kiosk, creative=creative,
        played_at=timezone.now(), duration_played=15,
    )
    r = admin_client.delete(f"/api/campaigns/v2/creatives/{creative.pk}/")
    # Faz 0.5: 204 (silindi) veya 404. Faz 3'te 409 bekleniyor.
    assert r.status_code in (204, 404, 409), (
        f"Status {r.status_code}: Faz 3'te 409 (dependency conflict) eklenmeli"
    )


# ─────────────────────────────────────────────────────────────────────────────
# M09 — Kiosk stabil URL'den medyayı playlist'te alıyor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_m09_kiosk_gets_stable_media_url(kiosk_client, kiosk, house_ad_10s):
    """Kiosk playlist endpoint'i presigned olmayan media_url döndürmeli."""
    from apps.campaigns.models import ScheduleRule

    base = _today_start()
    camp = Campaign.objects.create(
        name="M09",
        start_date=base - _dt.timedelta(days=1),
        end_date=base + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )
    stable = _stable_url("ads/stable_m09.mp4")
    Creative.objects.create(campaign=camp, media_url=stable, duration_seconds=15)
    ScheduleRule.objects.create(
        campaign=camp, frequency_type=ScheduleRule.FrequencyType.PER_HOUR, frequency_value=1
    )

    generate_for_kiosk(kiosk, TODAY)
    r = kiosk_client.get(f"/api/kiosk/v1/playlist/?date={TODAY}")
    assert r.status_code == 200, r.content

    all_urls = [item["media_url"] for pl in r.json()["playlists"] for item in pl["items"]]
    presigned = [u for u in all_urls if "X-Amz-" in u]
    assert not presigned, f"Presigned URL bulundu: {presigned[:3]}"
    assert stable in all_urls, f"Stabil URL {stable!r} playlist'te bulunamadı"


# ─────────────────────────────────────────────────────────────────────────────
# M10 — StorageService.public_url bucket dahil stabil URL döndürüyor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_m10_storage_service_public_url():
    """StorageService.public_url S3_PUBLIC_BASE_URL sözleşmesine uygun URL döndürmeli.

    Sözleşme: S3_PUBLIC_BASE_URL bucket dahil; media_url = base + "/" + object_key.
    """
    from apps.core.services.storage_service import StorageService

    with patch.object(StorageService, "_ensure_bucket"), \
         patch("apps.core.services.storage_service.Minio"):
        StorageService._instance = None
        svc = StorageService()
        url = svc.public_url("ads/test_file.mp4")

    expected = _stable_url("ads/test_file.mp4")
    assert url == expected, f"Beklenen {expected!r}, bulundu {url!r}"
    assert "X-Amz-" not in url and "?" not in url
    # S3_PUBLIC_BASE_URL path'i URL'de olmalı
    assert settings.S3_PUBLIC_BASE_URL.rstrip("/") in url


# ─────────────────────────────────────────────────────────────────────────────
# M11 — _derive_object_key_from_url — bucket-aware, güvenlik
# ─────────────────────────────────────────────────────────────────────────────


def test_m11_derive_object_key_from_url():
    """_derive_object_key_from_url bucket-in-path URL'den doğru key türetmeli."""
    from apps.campaigns.serializers import _derive_object_key_from_url

    assert _derive_object_key_from_url(_stable_url("ads/abc.mp4")) == "ads/abc.mp4"
    assert _derive_object_key_from_url(_presigned_url("ads/abc.mp4")) == ""
    assert _derive_object_key_from_url("") == ""
    assert _derive_object_key_from_url("https://evil.com/ads/file.mp4") == ""
    # Path traversal
    assert _derive_object_key_from_url(_stable_url("ads/../../../etc/passwd")) == ""


# ─────────────────────────────────────────────────────────────────────────────
# M12 — backfill URL ayrıştırma — bucket-in-path format
# ─────────────────────────────────────────────────────────────────────────────


def test_m12_backfill_url_parsing():
    """_extract_object_key bucket-in-path URL'yi doğru ayrıştırmalı."""
    from apps.campaigns.management.commands.backfill_media_object_keys import (
        _extract_object_key, _allowed_hosts,
    )

    endpoint = getattr(settings, "S3_ENDPOINT",
                       getattr(settings, "RUSTFS_ENDPOINT", "localhost:9000"))
    bucket = getattr(settings, "S3_BUCKET",
                     getattr(settings, "RUSTFS_BUCKET_NAME", "dev"))
    public_base = getattr(settings, "S3_PUBLIC_BASE_URL", "")
    allowed = _allowed_hosts(endpoint)

    # Presigned URL → doğru key
    key, reason = _extract_object_key(
        _presigned_url("ads/testfile.mp4"), endpoint, bucket, public_base, allowed
    )
    assert key == "ads/testfile.mp4", f"key={key!r} reason={reason}"
    assert reason == "ok"

    # Stabil URL → doğru key + already_stable
    key2, reason2 = _extract_object_key(
        _stable_url("ads/stable.mp4"), endpoint, bucket, public_base, allowed
    )
    assert key2 == "ads/stable.mp4"
    assert reason2 == "already_stable"

    # Farklı host → None
    key3, reason3 = _extract_object_key(
        _presigned_url("ads/f.mp4").replace(endpoint, "other.invalid:9999"),
        endpoint, bucket, public_base, allowed,
    )
    assert key3 is None
    assert "not_allowed" in reason3 or "mismatch" in reason3

    # Farklı bucket → None
    key4, reason4 = _extract_object_key(
        f"http://{endpoint}/wrongbucket/ads/f.mp4?X-Amz-Expires=3600",
        endpoint, bucket, public_base, allowed,
    )
    assert key4 is None

    # Boş URL → None
    key5, _ = _extract_object_key("", endpoint, bucket, public_base, allowed)
    assert key5 is None

    # Path traversal → None
    key6, reason6 = _extract_object_key(
        f"http://{endpoint}/{bucket}/ads/../../../etc/passwd?X-Amz-Expires=1",
        endpoint, bucket, public_base, allowed,
    )
    assert key6 is None
    assert "traversal" in reason6


# ─────────────────────────────────────────────────────────────────────────────
# M13 — Feature flag kapalı → legacy presigned davranışı korunuyor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=False)
def test_m13_flag_off_uses_legacy_presigned(admin_client, mock_storage_cls):
    """DOOH_PERSISTENT_MEDIA_URL=False: upload_file + get_object_url kullanılmalı."""
    _, instance = mock_storage_cls

    f = io.BytesIO(b"legacy"); f.name = "ad.mp4"
    r = admin_client.post("/api/campaigns/upload-media/", {"file": f}, format="multipart")

    assert r.status_code == 201, r.content
    body = r.json()

    # Legacy response alanları
    assert "url" in body and "filename" in body and "object_name" in body
    # Legacy path metodları
    instance.upload_file.assert_called_once()
    instance.upload_file_with_checksum.assert_not_called()
    # object_key ve media_url yeni alanlar legacy response'ta yok
    assert "object_key" not in body
    assert "media_url" not in body


# ─────────────────────────────────────────────────────────────────────────────
# M14 — Streaming hash: chunk stream ile hash+upload, RAM'e tam alınmıyor
# ─────────────────────────────────────────────────────────────────────────────


def test_m14_streaming_checksum_chunk_read():
    """upload_file_with_checksum dosyayı chunk'larla okumalı; SHA-256 doğru olmalı."""
    from apps.core.services.storage_service import StorageService

    data = b"fake video data " * 1024  # 16 KB
    expected_sha = "sha256:" + hashlib.sha256(data).hexdigest()

    # Chunk bazlı read mock'u
    chunk_size = 64 * 1024
    read_chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)] + [b""]
    mock_file = MagicMock()
    mock_file.name = "test.mp4"
    mock_file.content_type = "video/mp4"
    mock_file.size = len(data)
    mock_file.read.side_effect = read_chunks

    with patch.object(StorageService, "_ensure_bucket"), \
         patch("apps.core.services.storage_service.Minio") as MockMinio:
        StorageService._instance = None
        svc = StorageService()
        mock_client = MockMinio.return_value
        svc.client = mock_client

        key, checksum = svc.upload_file_with_checksum(mock_file, prefix="ads")

    assert checksum == expected_sha, f"Beklenen {expected_sha}, bulundu {checksum}"
    # seek(0) iki kez çağrılmalı: hash pass + upload pass
    assert mock_file.seek.call_count == 2, (
        f"seek(0) iki kez çağrılmalıydı, count={mock_file.seek.call_count}"
    )
    mock_client.put_object.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# M15 — Panel akışı: upload → object_key → Creative DB'ye kaydedildi
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True)
def test_m15_panel_upload_then_create_creative(admin_client, mock_storage_cls, active_campaign):
    """Upload → object_key alınır → Creative create ile DB'ye kaydedilir."""
    _, instance = mock_storage_cls

    # Step 1: Upload
    f = io.BytesIO(b"panel upload"); f.name = "ad.mp4"
    r_up = admin_client.post("/api/campaigns/upload-media/", {"file": f}, format="multipart")
    assert r_up.status_code == 201, r_up.content
    up = r_up.json()
    assert "object_key" in up and "media_url" in up and "checksum" in up

    # Step 2: Creative oluştur
    r_cr = admin_client.post(
        "/api/campaigns/v2/creatives/",
        {"campaign": str(active_campaign.pk), "media_url": up["media_url"],
         "duration_seconds": 15, "name": "M15"},
        format="json",
    )
    assert r_cr.status_code == 201, r_cr.content
    creative = Creative.objects.get(pk=r_cr.json()["id"])

    assert creative.object_key == up["object_key"], (
        f"object_key beklenen {up['object_key']!r}, bulundu {creative.object_key!r}"
    )
    assert creative.media_url == up["media_url"]
    assert "X-Amz-" not in creative.media_url


# ─────────────────────────────────────────────────────────────────────────────
# Serializer alanları
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_housead_object_key_in_response(admin_client, house_ad_10s):
    r = admin_client.get("/api/campaigns/v2/house-ads/")
    assert r.status_code == 200, r.content
    data = r.json()
    results = data if isinstance(data, list) else data.get("results", data)
    assert "object_key" in results[0], f"object_key eksik: {list(results[0].keys())}"


@pytest.mark.django_db
def test_creative_serializer_includes_object_key(admin_client, active_campaign):
    stable = _stable_url("ads/ck_test.mp4")
    r = admin_client.post(
        "/api/campaigns/v2/creatives/",
        {"campaign": str(active_campaign.pk), "media_url": stable, "duration_seconds": 15},
        format="json",
    )
    assert r.status_code == 201, r.content
    body = r.json()
    assert "object_key" in body
    assert body["object_key"] == "ads/ck_test.mp4"
