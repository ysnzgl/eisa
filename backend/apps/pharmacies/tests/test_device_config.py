from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.announcements.models import PharmacyDutyDay, PharmacyDutyMonth
from apps.pharmacies.models import Kiosk, KioskAudioAsset, KioskIdleAudio


pytestmark = pytest.mark.django_db


def test_existing_defaults_are_preserved(kiosk):
    assert kiosk.interaction_timeout_seconds == 20
    assert kiosk.idle_content_min_seconds == 10
    assert kiosk.idle_content_max_seconds == 12
    assert kiosk.idle_content_refresh_seconds == 300
    assert kiosk.idle_audio_delay_seconds == 1200
    assert kiosk.idle_audio_repeat_seconds == 300
    assert kiosk.idle_audio_enabled is False


def test_admin_updates_only_selected_kiosk(admin_client, kiosk, eczane):
    other = Kiosk.objects.create(
        eczane=eczane,
        ad="Diger Kiosk",
        mac_adresi="11:22:33:44:55:66",
        uygulama_anahtari="other-app-key-secure-48chars-xxxxxxxxxxxxxxxxxx",
    )
    response = admin_client.patch(
        f"/api/pharmacies/kiosks/{kiosk.pk}/",
        {
            "interaction_timeout_seconds": 45,
            "idle_content_min_seconds": 15,
            "idle_content_max_seconds": 25,
            "idle_content_refresh_seconds": 600,
            "idle_audio_delay_seconds": 1200,
        },
        format="json",
    )
    assert response.status_code == 200, response.content
    kiosk.refresh_from_db()
    other.refresh_from_db()
    assert kiosk.interaction_timeout_seconds == 45
    assert kiosk.idle_content_max_seconds == 25
    assert other.interaction_timeout_seconds == 20


def test_invalid_timing_range_rejected(admin_client, kiosk):
    response = admin_client.patch(
        f"/api/pharmacies/kiosks/{kiosk.pk}/",
        {"idle_content_min_seconds": 30, "idle_content_max_seconds": 10},
        format="json",
    )
    assert response.status_code == 400
    assert "idle_content_max_seconds" in response.json()


def test_sync_contains_device_config(kiosk_client, kiosk):
    kiosk.interaction_timeout_seconds = 35
    kiosk.idle_audio_delay_seconds = 900
    kiosk.save(update_fields=["interaction_timeout_seconds", "idle_audio_delay_seconds"])
    response = kiosk_client.get("/api/kiosk/v1/sync/")
    assert response.status_code == 200
    config = response.json()["device_config"]
    assert config["interaction_timeout_seconds"] == 35
    assert config["idle_audio_delay_seconds"] == 900
    assert config["idle_audio_repeat_seconds"] == 300
    assert config["idle_audio"]["enabled"] is False


def test_sync_contains_audio_schedule_and_pharmacy_duty_dates(kiosk_client, kiosk, eczane):
    today = timezone.localdate()
    month = today.replace(day=1)
    duty_month = PharmacyDutyMonth.objects.create(pharmacy=eczane, month=month)
    PharmacyDutyDay.objects.create(duty_month=duty_month, date=today)
    kiosk.idle_audio_schedule_mode = "BUSINESS_HOURS"
    kiosk.idle_audio_play_on_duty = True
    kiosk.save(update_fields=["idle_audio_schedule_mode", "idle_audio_play_on_duty"])

    response = kiosk_client.get("/api/kiosk/v1/sync/")
    assert response.status_code == 200
    config = response.json()["device_config"]
    assert config["idle_audio_schedule_mode"] == "BUSINESS_HOURS"
    assert config["idle_audio_play_on_duty"] is True
    assert today.isoformat() in config["idle_audio_duty_dates"]


def test_admin_uploads_mp3_and_sync_uses_authenticated_proxy(admin_client, kiosk, eczane):
    storage = MagicMock()
    storage.upload_file_with_checksum.side_effect = [
        ("kiosk-audio/first.mp3", "sha256:abc"),
        ("kiosk-audio/second.mp3", "sha256:def"),
    ]
    storage.public_url.side_effect = lambda key: f"https://files.example/{key}"
    first = SimpleUploadedFile("bir.mp3", b"ID3" + (b"\x00" * 64), content_type="audio/mpeg")
    second = SimpleUploadedFile("iki.mp3", b"ID3" + (b"\x01" * 64), content_type="audio/mpeg")
    with patch("apps.core.services.storage_service.StorageService", return_value=storage):
        response = admin_client.post(
            f"/api/pharmacies/kiosks/{kiosk.pk}/upload-idle-audio/",
            {"files": [first, second]},
            format="multipart",
        )
    assert response.status_code == 200, response.content
    kiosk.refresh_from_db()
    assert kiosk.idle_audio_enabled is True
    assert list(kiosk.idle_audio_files.values_list("original_name", "sira")) == [("bir.mp3", 0), ("iki.mp3", 1)]

    from rest_framework.test import APIClient
    kiosk_client = APIClient()
    kiosk_client.credentials(
        HTTP_AUTHORIZATION=f"AppKey {kiosk.uygulama_anahtari}",
        HTTP_X_KIOSK_MAC=kiosk.mac_adresi,
    )
    payload = kiosk_client.get("/api/kiosk/v1/sync/").json()["device_config"]["idle_audio"]
    assert payload["enabled"] is True
    assert payload["media_url"].endswith("/api/kiosk/v1/media/kiosk-audio/first.mp3")
    assert payload["checksum"] == "sha256:abc"
    assert [item["original_name"] for item in payload["files"]] == ["bir.mp3", "iki.mp3"]

    other = Kiosk.objects.create(
        eczane=eczane,
        ad="Diger Kiosk",
        mac_adresi="22:33:44:55:66:77",
        uygulama_anahtari="another-kiosk-app-key-secure-xxxxxxxxxxxxxxxx",
    )
    kiosk_client.credentials(
        HTTP_AUTHORIZATION=f"AppKey {other.uygulama_anahtari}",
        HTTP_X_KIOSK_MAC=other.mac_adresi,
    )
    assert kiosk_client.get("/api/kiosk/v1/media/kiosk-audio/first.mp3").status_code == 404


def test_non_audio_upload_rejected(admin_client, kiosk):
    bad = SimpleUploadedFile("not-audio.mp3", b"hello", content_type="audio/mpeg")
    response = admin_client.post(
        f"/api/pharmacies/kiosks/{kiosk.pk}/upload-idle-audio/",
        {"file": bad},
        format="multipart",
    )
    assert response.status_code == 400
    assert kiosk.idle_audio_enabled is False


def test_admin_can_choose_library_sounds_in_the_requested_order(admin_client, kiosk):
    first = KioskAudioAsset.objects.create(
        object_key="kiosk-audio/library-one.mp3", original_name="one.mp3", content_type="audio/mpeg"
    )
    second = KioskAudioAsset.objects.create(
        object_key="kiosk-audio/library-two.mp3", original_name="two.mp3", content_type="audio/mpeg"
    )
    response = admin_client.post(
        f"/api/pharmacies/kiosks/{kiosk.pk}/set-idle-audios/",
        {"audio_ids": [second.pk, first.pk]}, format="json",
    )
    assert response.status_code == 200, response.content
    kiosk.refresh_from_db()
    assert kiosk.idle_audio_enabled is True
    assert list(kiosk.idle_audio_files.values_list("audio_asset_id", "sira")) == [
        (second.pk, 0), (first.pk, 1),
    ]
    files = response.json()["idle_audio_files"]
    assert [item["asset_id"] for item in files] == [second.pk, first.pk]

    library = admin_client.get("/api/pharmacies/kiosks/idle-audio-library/")
    assert library.status_code == 200
    assert {item["id"] for item in library.json()} >= {first.pk, second.pk}


def test_admin_removes_audio_files_individually(admin_client, kiosk):
    first = KioskIdleAudio.objects.create(
        kiosk=kiosk, object_key="kiosk-audio/one.mp3", original_name="one.mp3",
        content_type="audio/mpeg", sira=0,
    )
    second = KioskIdleAudio.objects.create(
        kiosk=kiosk, object_key="kiosk-audio/two.mp3", original_name="two.mp3",
        content_type="audio/mpeg", sira=1,
    )
    kiosk.idle_audio_enabled = True
    kiosk.save(update_fields=["idle_audio_enabled"])

    response = admin_client.post(
        f"/api/pharmacies/kiosks/{kiosk.pk}/remove-idle-audio/",
        {"audio_id": first.pk}, format="json",
    )
    assert response.status_code == 200
    kiosk.refresh_from_db()
    assert kiosk.idle_audio_enabled is True
    assert list(kiosk.idle_audio_files.values_list("pk", flat=True)) == [second.pk]

    response = admin_client.post(
        f"/api/pharmacies/kiosks/{kiosk.pk}/remove-idle-audio/",
        {"audio_id": second.pk}, format="json",
    )
    assert response.status_code == 200
    kiosk.refresh_from_db()
    assert kiosk.idle_audio_enabled is False


def test_pharmacist_cannot_change_device_audio(eczaci_client, kiosk):
    response = eczaci_client.post(f"/api/pharmacies/kiosks/{kiosk.pk}/remove-idle-audio/")
    assert response.status_code == 403
