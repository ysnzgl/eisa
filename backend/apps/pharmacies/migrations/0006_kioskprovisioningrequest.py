"""Kiosk onay-bekleyen provision talepleri tablosu."""
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pharmacies", "0005_kiosk_is_online_kiosk_last_playlist_version"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KioskProvisioningRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("olusturulma_tarihi", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("guncellenme_tarihi", models.DateTimeField(auto_now_add=True)),
                ("surum", models.PositiveIntegerField(default=1, editable=False)),
                ("mac_adresi", models.CharField(db_index=True, max_length=17)),
                ("hostname", models.CharField(blank=True, default="", max_length=255)),
                ("device_metadata", models.JSONField(
                    blank=True, default=dict,
                    help_text="Guvenli cihaz/env metadata (token/secret icermez).",
                )),
                ("status", models.CharField(
                    choices=[("PENDING", "Onay Bekliyor"), ("APPROVED", "Onaylandi"), ("REJECTED", "Reddedildi")],
                    db_index=True, default="PENDING", max_length=16,
                )),
                ("last_seen_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("request_count", models.PositiveIntegerField(default=1)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True, default="")),
                ("olusturan", models.ForeignKey(
                    blank=True, editable=False, null=True,
                    on_delete=django.db.models.deletion.SET_NULL, related_name="+",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("guncelleyen", models.ForeignKey(
                    blank=True, editable=False, null=True,
                    on_delete=django.db.models.deletion.SET_NULL, related_name="+",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("approved_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="approved_provisioning_requests",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("rejected_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="rejected_provisioning_requests",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("kiosk", models.OneToOneField(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="provisioning_request",
                    to="pharmacies.kiosk",
                )),
            ],
            options={
                "verbose_name": "Kiosk Provision Talebi",
                "verbose_name_plural": "Kiosk Provision Talepleri",
                "db_table": "kiosk_provisioning_requests",
                "ordering": ("-olusturulma_tarihi",),
            },
        ),
    ]
