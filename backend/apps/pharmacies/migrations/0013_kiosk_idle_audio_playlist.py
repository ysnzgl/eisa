from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("pharmacies", "0012_kiosk_device_config_and_idle_audio"),
    ]

    operations = [
        migrations.AddField(
            model_name="kiosk",
            name="idle_audio_repeat_seconds",
            field=models.PositiveIntegerField(
                default=300,
                help_text="Ilk oynatimdan sonra etkilesime kadar sesler arasinda beklenecek sure.",
            ),
        ),
        migrations.CreateModel(
            name="KioskIdleAudio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("olusturulma_tarihi", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("guncellenme_tarihi", models.DateTimeField(auto_now_add=True)),
                ("surum", models.PositiveIntegerField(default=1, editable=False)),
                ("media_url", models.URLField(blank=True, default="", max_length=1000)),
                ("object_key", models.CharField(max_length=500)),
                ("checksum", models.CharField(blank=True, default="", max_length=80)),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(max_length=100)),
                ("sira", models.PositiveSmallIntegerField(default=0)),
                ("guncelleyen", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("kiosk", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="idle_audio_files", to="pharmacies.kiosk")),
                ("olusturan", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "kiosk_idle_audios",
                "ordering": ("sira", "id"),
            },
        ),
        migrations.AddConstraint(
            model_name="kioskidleaudio",
            constraint=models.UniqueConstraint(fields=("kiosk", "sira"), name="uniq_kiosk_idle_audio_sira"),
        ),
    ]
