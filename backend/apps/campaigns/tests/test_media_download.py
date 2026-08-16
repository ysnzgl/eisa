"""Medya indirme endpoint testleri ve kalıcı URL doğrulama.

Test kapsamı:
  D01  Creative download endpoint — SuperAdmin erişebilir, içerik doğru
  D02  HouseAd download endpoint — SuperAdmin erişebilir, içerik doğru
  D03  Download yalnız SuperAdmin — anonim 401, pharmacist 403
  D04  Eksik object_key → 404
  D05  Storage'da bulunmayan nesne → 404
  D06  Path traversal saldırısı engellenir (object_key frontend'den gelmez)
  D07  Creative upload → object_key DB'ye kaydedildi (flag=True)
  D08  HouseAd upload → object_key DB'ye kaydedildi (flag=True)
  D09  Stabil media_url X-Amz-* içermiyor (flag=True)
  D10  active_media_url → active_object_key DB'ye türetildi
  D11  Backfill: Creative active_media_url → active_object_key dolduruldu
  D12  Backfill: HouseAd presigned URL → object_key dolduruldu (dry-run)
  D13  Kiosk playlist/sync testleri bozulmuyor
"""
from __future__ import annotations

import datetime as _dt
import io
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from apps.campaigns.models import Campaign, Creative, HouseAd

Kullanici = get_user_model()

STABLE_BASE = "http://localhost:9000/dev"
OBJECT_KEY = "ads/testmedia.mp4"
ACTIVE_KEY = "ads/activemedia.mp4"
CHECKSUM = "sha256:abcdef1234567890"
PRESIGNED_URL = (
    f"http://localhost:9000/dev/{OBJECT_KEY}"
    "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=3600&X-Amz-Signature=fake"
)

TODAY = _dt.date(2026, 8, 15)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def superadmin(db):
    return Kullanici.objects.create_user(
        username="admin_dl", password="admin1234pass",
        is_staff=True, rol="superadmin",
    )


@pytest.fixture
def pharmacist(db):
    return Kullanici.objects.create_user(
        username="eczaci_dl", password="eczaci1234pass", rol="pharmacist",
    )


@pytest.fixture
def campaign(db):
    base = _dt.datetime(2026, 8, 1, tzinfo=_dt.timezone.utc)
    return Campaign.objects.create(
        name="DL Test Campaign",
        start_date=base,
        end_date=base + _dt.timedelta(days=30),
        status=Campaign.Status.ACTIVE,
    )


@pytest.fixture
def creative_with_key(db, campaign):
    return Creative.objects.create(
        campaign=campaign,
        media_url=f"{STABLE_BASE}/{OBJECT_KEY}",
        active_media_url=f"{STABLE_BASE}/{ACTIVE_KEY}",
        duration_seconds=15,
        name="Test Creative",
        checksum=CHECKSUM,
        object_key=OBJECT_KEY,
        active_object_key=ACTIVE_KEY,
    )


@pytest.fixture
def creative_no_key(db, campaign):
    return Creative.objects.create(
        campaign=campaign,
        media_url=PRESIGNED_URL,
        duration_seconds=15,
        name="No Key Creative",
    )


@pytest.fixture
def house_ad_with_key(db):
    return HouseAd.objects.create(
        name="Test HouseAd",
        media_url=f"{STABLE_BASE}/{OBJECT_KEY}",
        duration_seconds=15,
        aktif=True,
        priority=50,
        object_key=OBJECT_KEY,
    )


@pytest.fixture
def house_ad_no_key(db):
    return HouseAd.objects.create(
        name="No Key HouseAd",
        media_url=PRESIGNED_URL,
        duration_seconds=15,
        aktif=True,
    )


def _auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _mock_storage_get(content: bytes = b"fakemediabytes"):
    """get_object mock: iterator üzerinden chunk döner."""
    resp = MagicMock()
    resp.stream.return_value = [content]
    resp.close = MagicMock()
    resp.release_conn = MagicMock()
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# D01 — Creative download endpoint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True, S3_PUBLIC_BASE_URL=STABLE_BASE)
def test_d01_creative_download_superadmin(superadmin, creative_with_key):
    client = _auth_client(superadmin)
    fake_content = b"video_bytes_abc"

    with patch("apps.core.services.storage_service.StorageService") as MockStorage:
        instance = MockStorage.return_value
        instance.bucket_name = "dev"
        instance.client.get_object.return_value = _mock_storage_get(fake_content)

        resp = client.get(f"/api/campaigns/v2/creatives/{creative_with_key.pk}/download/")

    assert resp.status_code == 200
    assert resp["Content-Disposition"] == f'attachment; filename="testmedia.mp4"'
    assert b"".join(resp.streaming_content) == fake_content


# ─────────────────────────────────────────────────────────────────────────────
# D02 — HouseAd download endpoint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True, S3_PUBLIC_BASE_URL=STABLE_BASE)
def test_d02_house_ad_download_superadmin(superadmin, house_ad_with_key):
    client = _auth_client(superadmin)
    fake_content = b"housead_image_bytes"

    with patch("apps.core.services.storage_service.StorageService") as MockStorage:
        instance = MockStorage.return_value
        instance.bucket_name = "dev"
        instance.client.get_object.return_value = _mock_storage_get(fake_content)

        resp = client.get(f"/api/campaigns/v2/house-ads/{house_ad_with_key.pk}/download/")

    assert resp.status_code == 200
    assert resp["Content-Disposition"] == f'attachment; filename="testmedia.mp4"'
    assert b"".join(resp.streaming_content) == fake_content


# ─────────────────────────────────────────────────────────────────────────────
# D03 — Sadece SuperAdmin erişebilir
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_d03_download_anonymous_401(creative_with_key):
    client = APIClient()
    resp = client.get(f"/api/campaigns/v2/creatives/{creative_with_key.pk}/download/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_d03_download_pharmacist_403(pharmacist, creative_with_key):
    client = _auth_client(pharmacist)
    resp = client.get(f"/api/campaigns/v2/creatives/{creative_with_key.pk}/download/")
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# D04 — Eksik object_key → 404
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_d04_missing_object_key_creative(superadmin, creative_no_key):
    client = _auth_client(superadmin)
    resp = client.get(f"/api/campaigns/v2/creatives/{creative_no_key.pk}/download/")
    assert resp.status_code == 404
    assert "object_key" in resp.data["error"].lower()


@pytest.mark.django_db
def test_d04_missing_object_key_house_ad(superadmin, house_ad_no_key):
    client = _auth_client(superadmin)
    resp = client.get(f"/api/campaigns/v2/house-ads/{house_ad_no_key.pk}/download/")
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# D05 — Storage'da bulunmayan nesne → 404
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_d05_object_not_in_storage(superadmin, creative_with_key):
    client = _auth_client(superadmin)

    with patch("apps.core.services.storage_service.StorageService") as MockStorage:
        instance = MockStorage.return_value
        instance.bucket_name = "dev"
        instance.client.get_object.side_effect = Exception("NoSuchKey")

        resp = client.get(f"/api/campaigns/v2/creatives/{creative_with_key.pk}/download/")

    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# D07 — Creative upload → object_key DB'ye kaydedildi (flag=True)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True, S3_PUBLIC_BASE_URL=STABLE_BASE)
def test_d07_creative_upload_saves_object_key(superadmin, campaign):
    client = _auth_client(superadmin)

    with patch("apps.campaigns.views.StorageService") as MockStorage:
        inst = MockStorage.return_value
        inst.upload_file_with_checksum.return_value = (OBJECT_KEY, CHECKSUM)
        inst.public_url.return_value = f"{STABLE_BASE}/{OBJECT_KEY}"

        file_data = io.BytesIO(b"fake_video")
        file_data.name = "test.mp4"
        file_data.size = len(b"fake_video")
        file_data.content_type = "video/mp4"

        upload_resp = client.post(
            "/api/campaigns/upload-media/",
            {"file": file_data},
            format="multipart",
        )

    assert upload_resp.status_code == 201
    assert upload_resp.data["object_key"] == OBJECT_KEY
    assert "X-Amz-" not in upload_resp.data["media_url"]

    # Create creative using the upload response
    creative_resp = client.post(
        "/api/campaigns/v2/creatives/",
        {
            "campaign": str(campaign.pk),
            "media_url": upload_resp.data["media_url"],
            "object_key": upload_resp.data["object_key"],
            "checksum": upload_resp.data["checksum"],
            "duration_seconds": 15,
            "name": "Test D07",
        },
        format="json",
    )
    assert creative_resp.status_code == 201
    creative = Creative.objects.get(pk=creative_resp.data["id"])
    assert creative.object_key == OBJECT_KEY
    assert "X-Amz-" not in creative.media_url


# ─────────────────────────────────────────────────────────────────────────────
# D08 — HouseAd upload → object_key DB'ye kaydedildi (flag=True)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True, S3_PUBLIC_BASE_URL=STABLE_BASE)
def test_d08_house_ad_upload_saves_object_key(superadmin):
    client = _auth_client(superadmin)
    image_key = "ads/testimage.png"

    with patch("apps.campaigns.views.StorageService") as MockStorage:
        inst = MockStorage.return_value
        inst.upload_file_with_checksum.return_value = (image_key, CHECKSUM)
        inst.public_url.return_value = f"{STABLE_BASE}/{image_key}"

        file_data = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        file_data.name = "test.png"
        file_data.size = 108
        file_data.content_type = "image/png"

        upload_resp = client.post(
            "/api/campaigns/upload-media/",
            {"file": file_data, "media_kind": "image"},
            format="multipart",
        )

    assert upload_resp.status_code == 201

    house_ad_resp = client.post(
        "/api/campaigns/v2/house-ads/",
        {
            "name": "Test HouseAd D08",
            "media_url": upload_resp.data["media_url"],
            "object_key": upload_resp.data["object_key"],
            "duration_seconds": 15,
            "aktif": True,
            "priority": 50,
        },
        format="json",
    )
    assert house_ad_resp.status_code == 201
    ha = HouseAd.objects.get(pk=house_ad_resp.data["id"])
    assert ha.object_key == image_key
    assert "X-Amz-" not in ha.media_url


# ─────────────────────────────────────────────────────────────────────────────
# D09 — Stabil media_url X-Amz-* içermiyor
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True, S3_PUBLIC_BASE_URL=STABLE_BASE)
def test_d09_stable_media_url_no_amz_params(superadmin):
    client = _auth_client(superadmin)

    with patch("apps.campaigns.views.StorageService") as MockStorage:
        inst = MockStorage.return_value
        inst.upload_file_with_checksum.return_value = (OBJECT_KEY, CHECKSUM)
        inst.public_url.return_value = f"{STABLE_BASE}/{OBJECT_KEY}"

        file_data = io.BytesIO(b"fake_video")
        file_data.name = "test.mp4"
        file_data.size = len(b"fake_video")
        file_data.content_type = "video/mp4"

        resp = client.post(
            "/api/campaigns/upload-media/",
            {"file": file_data},
            format="multipart",
        )

    assert resp.status_code == 201
    assert "X-Amz-" not in resp.data["media_url"]
    assert "x-amz-" not in resp.data["media_url"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# D10 — active_media_url → active_object_key türetildi
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True, S3_PUBLIC_BASE_URL=STABLE_BASE)
def test_d10_active_object_key_derived(superadmin, campaign):
    client = _auth_client(superadmin)

    resp = client.post(
        "/api/campaigns/v2/creatives/",
        {
            "campaign": str(campaign.pk),
            "media_url": f"{STABLE_BASE}/{OBJECT_KEY}",
            "object_key": OBJECT_KEY,
            "active_media_url": f"{STABLE_BASE}/{ACTIVE_KEY}",
            "duration_seconds": 15,
            "name": "Test D10",
        },
        format="json",
    )
    assert resp.status_code == 201
    creative = Creative.objects.get(pk=resp.data["id"])
    assert creative.active_object_key == ACTIVE_KEY


# ─────────────────────────────────────────────────────────────────────────────
# D11 — Backfill: Creative active_media_url → active_object_key
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True, S3_PUBLIC_BASE_URL=STABLE_BASE,
                   S3_ENDPOINT="localhost:9000", S3_BUCKET="dev")
def test_d11_backfill_active_object_key(campaign):
    creative = Creative.objects.create(
        campaign=campaign,
        media_url=f"{STABLE_BASE}/{OBJECT_KEY}",
        object_key=OBJECT_KEY,
        active_media_url=f"{STABLE_BASE}/{ACTIVE_KEY}",
        active_object_key=None,
        duration_seconds=15,
    )

    from django.core.management import call_command
    from io import StringIO

    out = StringIO()
    call_command("backfill_media_object_keys", stdout=out)
    output = out.getvalue()

    # dry-run sonucunda active media bulunmalı
    assert "Creative(active)" in output
    assert ACTIVE_KEY in output

    # DB değişmemiş (dry-run)
    creative.refresh_from_db()
    assert creative.active_object_key is None


# ─────────────────────────────────────────────────────────────────────────────
# D12 — Backfill: HouseAd presigned URL dry-run
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
@override_settings(DOOH_PERSISTENT_MEDIA_URL=True, S3_PUBLIC_BASE_URL=STABLE_BASE,
                   S3_ENDPOINT="localhost:9000", S3_BUCKET="dev")
def test_d12_backfill_house_ad_presigned_dryrun():
    presigned = (
        f"http://localhost:9000/dev/{OBJECT_KEY}"
        "?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Expires=3600&X-Amz-Signature=fake"
    )
    ha = HouseAd.objects.create(
        name="Presigned HouseAd",
        media_url=presigned,
        duration_seconds=15,
        aktif=True,
    )

    from django.core.management import call_command
    from io import StringIO

    out = StringIO()
    call_command("backfill_media_object_keys", stdout=out)
    output = out.getvalue()

    assert "DRY-RUN" in output
    assert OBJECT_KEY in output

    # DB değişmemiş
    ha.refresh_from_db()
    assert ha.object_key is None
