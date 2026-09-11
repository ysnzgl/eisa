from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_existing_audio_to_library(apps, schema_editor):
    AudioAsset = apps.get_model("pharmacies", "KioskAudioAsset")
    Assignment = apps.get_model("pharmacies", "KioskIdleAudio")
    for assignment in Assignment.objects.filter(audio_asset__isnull=True).iterator():
        asset = AudioAsset.objects.create(
            media_url=assignment.media_url,
            object_key=assignment.object_key,
            checksum=assignment.checksum,
            original_name=assignment.original_name,
            content_type=assignment.content_type,
            olusturan_id=assignment.olusturan_id,
            guncelleyen_id=assignment.guncelleyen_id,
        )
        assignment.audio_asset_id = asset.pk
        assignment.save(update_fields=["audio_asset"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("pharmacies", "0013_kiosk_idle_audio_playlist"),
    ]

    operations = [
        migrations.CreateModel(
            name="KioskAudioAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("olusturulma_tarihi", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("guncellenme_tarihi", models.DateTimeField(auto_now_add=True)),
                ("surum", models.PositiveIntegerField(default=1, editable=False)),
                ("media_url", models.URLField(blank=True, default="", max_length=1000)),
                ("object_key", models.CharField(max_length=500, unique=True)),
                ("checksum", models.CharField(blank=True, default="", max_length=80)),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=100)),
                ("aktif", models.BooleanField(default=True)),
                ("guncelleyen", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("olusturan", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "kiosk_audio_assets", "ordering": ("original_name", "id")},
        ),
        migrations.AddField(
            model_name="kioskidleaudio",
            name="audio_asset",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="kiosk_atamalari", to="pharmacies.kioskaudioasset"),
        ),
        migrations.RunPython(copy_existing_audio_to_library, migrations.RunPython.noop),
    ]
