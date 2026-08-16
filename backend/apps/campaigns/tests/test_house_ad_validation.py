"""HouseAd image-only validasyon testleri (Faz 1).

HA-01  media_kind=image + video MIME → 400
HA-02  media_kind=image + sahte uzantı (JPEG magic, video/mp4 MIME) → 400
HA-03  media_kind=image + geçerli JPEG → 201
HA-04  media_kind=image + geçerli PNG → 201
HA-05  media_kind=image + geçerli WebP → 201
HA-06  media_kind=image + magic/MIME uyuşmazlığı (PNG magic + image/jpeg) → 400
HA-07  media_kind yok (creative upload) + video MIME → 201  (geriye uyumlu)
HA-08  HouseAdSerializer.validate_media_url video uzantısı → ValidationError
HA-09  HouseAdSerializer.validate_media_url görsel URL → geçer
HA-10  duration=45 yeni kayıt → 201
HA-11  duration=20 yeni kayıt → 400
HA-12  duration=15→15 legacy güncelleme → 200
HA-13  duration=20→20 legacy güncelleme → 200  (değişmeden koruma)
"""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from rest_framework.test import APIRequestFactory

from apps.campaigns.serializers import HouseAdSerializer


# ─── Magic-byte yardımcıları ──────────────────────────────────────────────────

JPEG_MAGIC = b"\xff\xd8\xff" + b"\xe0" * 9        # minimal JPEG header
PNG_MAGIC  = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4  # PNG signature
WEBP_MAGIC = b"RIFF\x00\x00\x00\x00WEBP"          # WebP (12 bytes)

MOCK_OBJ_KEY = "ads/testimage_x.png"
MOCK_CHECKSUM = "sha256:abcdef1234567890"
MOCK_URL = "http://localhost:9000/dev/ads/testimage_x.png"


@pytest.fixture()
def mock_storage_cls():
    with patch("apps.campaigns.views.StorageService") as MockCls:
        inst = MockCls.return_value
        inst.upload_file_with_checksum.return_value = (MOCK_OBJ_KEY, MOCK_CHECKSUM)
        inst.public_url.return_value = MOCK_URL
        inst.upload_file.return_value = MOCK_OBJ_KEY
        inst.get_object_url.return_value = MOCK_URL
        yield MockCls, inst


def _upload(admin_client, content: bytes, filename: str, content_type: str, media_kind: str | None = None):
    f = io.BytesIO(content)
    f.name = filename
    data = {"file": f}
    if media_kind is not None:
        data["media_kind"] = media_kind
    return admin_client.post("/api/campaigns/upload-media/", data, format="multipart",
                             CONTENT_TYPE=None)  # let DRF set multipart boundary


# ─── HA-01: video MIME image-only modda reddedilir ───────────────────────────

@pytest.mark.django_db
def test_ha01_video_mime_rejected_in_image_mode(admin_client, mock_storage_cls):
    fake_mp4 = b"\x00\x00\x00\x18ftyp" + b"\x00" * 20
    r = _upload(admin_client, fake_mp4, "ad.mp4", "video/mp4", media_kind="image")
    assert r.status_code == 400
    assert "PNG/JPEG/WebP" in r.json().get("error", "")


# ─── HA-02: JPEG magic + video/mp4 MIME → magic-byte öncesinde MIME reddi ───

@pytest.mark.django_db
def test_ha02_jpeg_magic_with_video_mime_rejected(admin_client, mock_storage_cls):
    r = _upload(admin_client, JPEG_MAGIC + b"\x00" * 50, "tricky.mp4", "video/mp4", media_kind="image")
    assert r.status_code == 400


# ─── HA-03: Geçerli JPEG kabul edilir ────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.django_db(transaction=False)
def test_ha03_valid_jpeg_accepted(admin_client, mock_storage_cls):
    r = _upload(admin_client, JPEG_MAGIC + b"\x00" * 100, "photo.jpg", "image/jpeg", media_kind="image")
    assert r.status_code == 201, r.content


# ─── HA-04: Geçerli PNG kabul edilir ─────────────────────────────────────────

@pytest.mark.django_db
def test_ha04_valid_png_accepted(admin_client, mock_storage_cls):
    r = _upload(admin_client, PNG_MAGIC + b"\x00" * 100, "img.png", "image/png", media_kind="image")
    assert r.status_code == 201, r.content


# ─── HA-05: Geçerli WebP kabul edilir ────────────────────────────────────────

@pytest.mark.django_db
def test_ha05_valid_webp_accepted(admin_client, mock_storage_cls):
    r = _upload(admin_client, WEBP_MAGIC + b"\x00" * 50, "img.webp", "image/webp", media_kind="image")
    assert r.status_code == 201, r.content


# ─── HA-06: PNG magic + image/jpeg MIME uyuşmazlığı → 400 ───────────────────

@pytest.mark.django_db
def test_ha06_magic_mime_mismatch_rejected(admin_client, mock_storage_cls):
    r = _upload(admin_client, PNG_MAGIC + b"\x00" * 50, "fake.jpg", "image/jpeg", media_kind="image")
    assert r.status_code == 400
    assert "MIME" in r.json().get("error", "")


# ─── HA-07: media_kind yok → video MIME mevcut ALLOWED_TYPES ile geçer ───────

@pytest.mark.django_db
def test_ha07_no_media_kind_video_still_accepted(admin_client, mock_storage_cls):
    fake_mp4 = b"\x00\x00\x00\x18ftyp" + b"\x00" * 20
    r = _upload(admin_client, fake_mp4, "ad.mp4", "video/mp4", media_kind=None)
    assert r.status_code == 201, r.content


# ─── HA-08: Serializer artık video URL kabul eder (HouseAd video desteği eklendi) ──

def test_ha08_serializer_accepts_video_url():
    """HouseAd artık video dosyalarını da destekliyor (görsel kısıtlaması kaldırıldı)."""
    s = HouseAdSerializer(data={
        "name": "Test",
        "media_url": "https://cdn.example.com/ads/promo.mp4",
        "duration_seconds": 15,
    })
    assert s.is_valid(), s.errors


# ─── HA-09: Serializer görsel URL kabul ──────────────────────────────────────

@pytest.mark.django_db
def test_ha09_serializer_accepts_image_url(db):
    s = HouseAdSerializer(data={
        "name": "Test",
        "media_url": "https://cdn.example.com/ads/promo.png",
        "duration_seconds": 15,
    })
    assert s.is_valid(), s.errors


# ─── HA-10: duration=45 yeni kayıt → geçer ───────────────────────────────────

@pytest.mark.django_db
def test_ha10_duration_45_accepted(db):
    s = HouseAdSerializer(data={
        "name": "T45",
        "media_url": "https://cdn.example.com/ads/img.webp",
        "duration_seconds": 45,
    })
    assert s.is_valid(), s.errors


# ─── HA-11: duration=20 yeni kayıt → grid uyumsuzluk hatası ─────────────────

@pytest.mark.django_db
def test_ha11_duration_20_rejected(db):
    s = HouseAdSerializer(data={
        "name": "T20",
        "media_url": "https://cdn.example.com/ads/img.png",
        "duration_seconds": 20,
    })
    assert not s.is_valid()
    assert "duration_seconds" in s.errors


# ─── HA-12: duration=15→15 legacy güncelleme → geçer ────────────────────────

@pytest.mark.django_db
def test_ha12_legacy_duration_unchanged_update(db):
    from apps.campaigns.models import HouseAd
    obj = HouseAd.objects.create(
        name="Legacy", media_url="https://cdn.example.com/ads/old.png",
        duration_seconds=15, aktif=True,
    )
    s = HouseAdSerializer(obj, data={
        "name": "Legacy Updated",
        "media_url": "https://cdn.example.com/ads/old.png",
        "duration_seconds": 15,
    }, partial=False)
    assert s.is_valid(), s.errors


# ─── HA-13: duration=20→20 legacy değer değişmeden → geçer ──────────────────

@pytest.mark.django_db
def test_ha13_legacy_nonstandard_duration_unchanged(db):
    from apps.campaigns.models import HouseAd
    obj = HouseAd.objects.create(
        name="Legacy20", media_url="https://cdn.example.com/ads/old.png",
        duration_seconds=20, aktif=True,
    )
    s = HouseAdSerializer(obj, data={
        "name": "Legacy20",
        "media_url": "https://cdn.example.com/ads/old.png",
        "duration_seconds": 20,
    }, partial=False)
    assert s.is_valid(), s.errors
