from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


SYSTEM_ANNOUNCEMENTS = (
    (
        "DUTY_NEXT_MONTH_MISSING",
        "Gelecek Ay Nöbet Bilginiz Eksik",
        "Gelecek ay için nöbet günlerinizi girin veya nöbetiniz olmadığını belirtin.",
    ),
    (
        "DUTY_CURRENT_MONTH_MISSING",
        "Bu Ay Nöbet Bilginiz Eksik",
        "Bu ay için nöbet günlerinizi girin veya nöbetiniz olmadığını belirtin.",
    ),
)


def seed_system_announcements(apps, schema_editor):
    Announcement = apps.get_model("announcements", "Announcement")
    for system_key, title, message in SYSTEM_ANNOUNCEMENTS:
        Announcement.objects.get_or_create(
            system_key=system_key,
            defaults={
                "kind": "SYSTEM",
                "title": title,
                "message": message,
                "action_label": "Nöbet Günlerini Gir",
                "severity": "ACTION_REQUIRED",
                "active": True,
                "recurrence": "ONCE",
                "target_scope": "ALL",
            },
        )


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("lookups", "0002_remove_il_plaka"),
        ("pharmacies", "0009_kiosk_last_ip"),
    ]
    operations = [
        migrations.CreateModel(
            name="Announcement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("olusturulma_tarihi", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("guncellenme_tarihi", models.DateTimeField(auto_now_add=True)),
                ("surum", models.PositiveIntegerField(default=1, editable=False)),
                ("kind", models.CharField(choices=[("GENERAL", "Genel duyuru"), ("SYSTEM", "Sistem duyurusu")], db_index=True, default="GENERAL", max_length=12)),
                ("system_key", models.CharField(blank=True, choices=[("DUTY_NEXT_MONTH_MISSING", "Gelecek ay nöbet bilgisi eksik"), ("DUTY_CURRENT_MONTH_MISSING", "Bu ay nöbet bilgisi eksik")], editable=False, max_length=64, null=True, unique=True)),
                ("title", models.CharField(max_length=200)),
                ("message", models.TextField()),
                ("action_label", models.CharField(blank=True, default="", max_length=80)),
                ("severity", models.CharField(choices=[("INFO", "Bilgilendirme"), ("WARNING", "Uyarı"), ("ACTION_REQUIRED", "İşlem gerekli")], default="INFO", max_length=24)),
                ("active", models.BooleanField(db_index=True, default=True)),
                ("recurrence", models.CharField(choices=[("ONCE", "Tek seferlik"), ("DAILY", "Günlük"), ("WEEKLY", "Haftalık"), ("MONTHLY", "Aylık")], default="ONCE", max_length=16)),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("weekdays", models.JSONField(blank=True, default=list, help_text="Pazartesi=0 ... Pazar=6")),
                ("monthly_mode", models.CharField(blank=True, choices=[("SPECIFIC_DAY", "Ayın belirli günü"), ("DAY_RANGE", "Ayın belirli gün aralığı"), ("FIRST_N_DAYS", "Ayın ilk N günü"), ("LAST_N_DAYS", "Ayın son N günü"), ("LAST_WEEK", "Ayın son haftası")], default="", max_length=24)),
                ("monthly_day_start", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("monthly_day_end", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("monthly_day_count", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("target_scope", models.CharField(choices=[("ALL", "Tüm eczaneler"), ("PROVINCE", "İl"), ("DISTRICT", "İlçe"), ("PHARMACY", "Eczane")], default="ALL", max_length=16)),
                ("guncelleyen", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("olusturan", models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("target_district", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="announcements", to="lookups.ilce")),
                ("target_pharmacy", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="announcements", to="pharmacies.eczane")),
                ("target_province", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="announcements", to="lookups.il")),
            ],
            options={"db_table": "announcements", "ordering": ("-olusturulma_tarihi",)},
        ),
        migrations.CreateModel(
            name="AnnouncementRead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("occurrence_date", models.DateField()),
                ("read_at", models.DateTimeField(auto_now_add=True)),
                ("announcement", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reads", to="announcements.announcement")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="announcement_reads", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "announcement_reads"},
        ),
        migrations.CreateModel(
            name="PharmacyDutyMonth",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.DateField(help_text="Ayın ilk günü")),
                ("has_no_duty", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("pharmacy", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="duty_months", to="pharmacies.eczane")),
                ("updated_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "pharmacy_duty_months"},
        ),
        migrations.CreateModel(
            name="PharmacyDutyDay",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("duty_month", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="days", to="announcements.pharmacydutymonth")),
            ],
            options={"db_table": "pharmacy_duty_days", "ordering": ("date",)},
        ),
        migrations.AddConstraint(
            model_name="announcementread",
            constraint=models.UniqueConstraint(fields=("announcement", "user", "occurrence_date"), name="uniq_announcement_user_occurrence"),
        ),
        migrations.AddConstraint(
            model_name="pharmacydutymonth",
            constraint=models.UniqueConstraint(fields=("pharmacy", "month"), name="uniq_pharmacy_duty_month"),
        ),
        migrations.AddConstraint(
            model_name="pharmacydutyday",
            constraint=models.UniqueConstraint(fields=("duty_month", "date"), name="uniq_duty_month_date"),
        ),
        migrations.RunPython(seed_system_announcements, migrations.RunPython.noop),
    ]
