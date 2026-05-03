from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("actor_repr", models.CharField(blank=True, default="", max_length=255)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("create", "Create"),
                            ("update", "Update"),
                            ("delete", "Delete"),
                            ("login", "Login"),
                            ("login_failed", "Login Failed"),
                            ("kiosk_online", "Kiosk Online"),
                            ("kiosk_offline", "Kiosk Offline"),
                            ("kiosk_heartbeat", "Kiosk Heartbeat"),
                            ("regenerate_key", "Regenerate App Key"),
                            ("other", "Other"),
                        ],
                        max_length=32,
                    ),
                ),
                ("target_type", models.CharField(blank=True, default="", max_length=64)),
                ("target_id", models.CharField(blank=True, default="", max_length=64)),
                ("summary", models.CharField(blank=True, default="", max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("kiosk_mac", models.CharField(blank=True, default="", max_length=17)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "audit_logs",
                "ordering": ("-created_at",),
                "indexes": [
                    models.Index(
                        fields=["action", "created_at"], name="audit_logs_action_b3f2c8_idx"
                    ),
                    models.Index(
                        fields=["target_type", "target_id"],
                        name="audit_logs_target__d4a1b0_idx",
                    ),
                    models.Index(
                        fields=["kiosk_mac", "created_at"],
                        name="audit_logs_kiosk_m_e5c2a1_idx",
                    ),
                ],
            },
        ),
    ]
