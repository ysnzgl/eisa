"""Migration 0026: Creative.active_object_key alanı eklendi.

Faz 0.5+ backfill: active_media_url için canonical S3 object key.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0025_faz3_playlog_status_idempotency"),
    ]

    operations = [
        migrations.AddField(
            model_name="creative",
            name="active_object_key",
            field=models.CharField(
                blank=True,
                help_text="active_media_url icin S3/RustFS obje anahtarı (örn. ads/abc123.mp4). NULL ise backfill_media_object_keys komutuyla doldurulabilir.",
                max_length=512,
                null=True,
            ),
        ),
    ]
