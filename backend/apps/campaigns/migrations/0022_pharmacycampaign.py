"""
PharmacyCampaign modeli eklendi.

Eczacı paneli kampanyaları için bağımsız model.
Kiosk playlist, scheduler, offline sync ve PlayLog sisteminden tamamen bağımsız.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid
import apps.campaigns.models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0021_creative_active_media_url"),
        ("pharmacies", "0008_faz4_faz5_kiosk_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PharmacyCampaign",
            fields=[
                ("olusturulma_tarihi", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "olusturan",
                    models.ForeignKey(
                        blank=True, editable=False, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("guncellenme_tarihi", models.DateTimeField(auto_now_add=True)),
                (
                    "guncelleyen",
                    models.ForeignKey(
                        blank=True, editable=False, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("surum", models.PositiveIntegerField(default=1, editable=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                (
                    "media_url",
                    models.URLField(
                        max_length=2048,
                        validators=[apps.campaigns.models._https_url_validator],
                        help_text="Yatay kampanya görseli (eczacı panelinde şerit ve overlay'de gösterilir).",
                    ),
                ),
                (
                    "object_key",
                    models.CharField(
                        blank=True,
                        max_length=512,
                        null=True,
                        help_text="S3/RustFS obje anahtarı (upload servisinden türetilir).",
                    ),
                ),
                ("start_at", models.DateTimeField(help_text="Kampanyanın yayın başlangıç tarihi ve saati.")),
                ("end_at", models.DateTimeField(help_text="Kampanyanın yayın bitiş tarihi ve saati.")),
                (
                    "duration_seconds",
                    models.PositiveSmallIntegerField(
                        default=10,
                        help_text="Her döngüde gösterim süresi (saniye).",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Pasif kampanyalar feed'de görünmez.",
                    ),
                ),
                (
                    "target_pharmacies",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Hedef eczaneler. En az bir eczane seçilmelidir.",
                        related_name="pharmacy_campaigns",
                        to="pharmacies.eczane",
                    ),
                ),
            ],
            options={
                "verbose_name": "Pharmacy Campaign",
                "verbose_name_plural": "Pharmacy Campaigns",
                "db_table": "pharmacy_campaigns",
                "ordering": ["-olusturulma_tarihi"],
                "indexes": [
                    models.Index(fields=["is_active", "start_at", "end_at"], name="pharmacy_camp_active_date_idx"),
                ],
            },
        ),
    ]
