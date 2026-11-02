"""Veri temizligi — eski sponsorluk verisini sil (RunPython, semadan ONCE).

Spec geregi: tum Campaign satirlari (Creative + PlaylistItem cascade), tum
Playlist ve GenerationJob satirlari silinir; PlayLog satirlari korunur
(creative -> NULL). Ardindan her aktif kiosk icin horizon gunlerinde PENDING
GenerationJob olusturulur; boylece kiosklar daha yuksek versiyonlu BOS program
alir ve eski cache'lenmis reklamlari oynatmayi birakir.

Bu migration bilincli olarak SADECE veri islemi yapar (ALTER TABLE yok);
sema degisiklikleri bir sonraki migration'dadir (PostgreSQL uyumu).
"""
from __future__ import annotations

import datetime as _dt
import zoneinfo

from django.conf import settings
from django.db import migrations

_ISTANBUL_TZ = zoneinfo.ZoneInfo("Europe/Istanbul")


def _horizon_dates():
    horizon = int(getattr(settings, "DOOH_HORIZON_DAYS", 3) or 3)
    today = _dt.datetime.now(_ISTANBUL_TZ).date()
    return [today + _dt.timedelta(days=i) for i in range(horizon)]


def cleanup_sponsorship_data(apps, schema_editor):
    """Eski sponsorluk verisini sil + aktif kiosklar icin PENDING is olustur."""
    Campaign = apps.get_model("campaigns", "Campaign")
    Playlist = apps.get_model("campaigns", "Playlist")
    PlayLog = apps.get_model("campaigns", "PlayLog")
    GenerationJob = apps.get_model("campaigns", "GenerationJob")
    Kiosk = apps.get_model("pharmacies", "Kiosk")

    # PlayLog korunur; creative referansi NULL'a cekilir (analitik tarihçe kalir).
    PlayLog.objects.filter(creative__isnull=False).update(creative=None)

    # Playlist (PlaylistItem cascade) ve mevcut tum isler silinir.
    Playlist.objects.all().delete()
    GenerationJob.objects.all().delete()

    # Campaign silinir -> Creative + (kalan) PlaylistItem cascade.
    Campaign.objects.all().delete()

    # Aktif kiosklar icin horizon gunlerinde PENDING is -> yuksek versiyonlu bos program.
    dates = _horizon_dates()
    jobs = []
    for kiosk_id in Kiosk.objects.filter(aktif=True).values_list("id", flat=True):
        for d in dates:
            jobs.append(GenerationJob(
                target_date=d,
                kiosk_id=kiosk_id,
                status="PENDING",
                triggered_by="data_cleanup",
                dedupe_key=f"{kiosk_id}:{d.isoformat()}",
            ))
    if jobs:
        GenerationJob.objects.bulk_create(jobs, ignore_conflicts=True)


def noop_reverse(apps, schema_editor):
    """Geri alinamaz veri temizligi — no-op reverse."""


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0032_proxy_presigned_media_urls"),
    ]

    operations = [
        migrations.RunPython(cleanup_sponsorship_data, noop_reverse),
    ]
