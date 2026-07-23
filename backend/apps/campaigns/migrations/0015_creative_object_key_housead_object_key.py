"""Faz 0.5 — Creative ve HouseAd modellerine ``object_key`` alanı eklenir.

K5 gereği: nullable ekle → backfill → doğrula → constraint (ileriki fazda).
Bu migration additive ve reversible'dır; mevcut kayıtları değiştirmez.
NOT NULL/unique constraint bu fazda eklenmez.
Backfill için: ``python manage.py backfill_media_object_keys --help``
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0014_hourplan_dayplan"),
    ]

    operations = [
        migrations.AddField(
            model_name="creative",
            name="object_key",
            field=models.CharField(
                null=True,
                blank=True,
                help_text=(
                    "S3/RustFS obje anahtarı (örn. ads/abc123.mp4). "
                    "Kalıcı media_url üretiminde kullanılır. "
                    "NULL ise backfill_media_object_keys komutuyla doldurulabilir."
                ),
                max_length=512,
            ),
        ),
        migrations.AddField(
            model_name="housead",
            name="object_key",
            field=models.CharField(
                null=True,
                blank=True,
                help_text=(
                    "S3/RustFS obje anahtarı (örn. ads/abc123.mp4). "
                    "Kalıcı media_url üretiminde kullanılır. "
                    "NULL ise backfill_media_object_keys komutuyla doldurulabilir."
                ),
                max_length=512,
            ),
        ),
    ]
