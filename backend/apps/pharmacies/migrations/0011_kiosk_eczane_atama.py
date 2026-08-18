from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill(apps, schema_editor):
    Kiosk = apps.get_model("pharmacies", "Kiosk")
    Atama = apps.get_model("pharmacies", "KioskEczaneAtama")
    db = schema_editor.connection.alias
    rows = []
    for kiosk in Kiosk.objects.using(db).all().iterator():
        rows.append(Atama(
            kiosk_id=kiosk.pk,
            eczane_id=kiosk.eczane_id,
            baslangic_zamani=kiosk.olusturulma_tarihi,
            olusturulma_tarihi=kiosk.olusturulma_tarihi,
            guncellenme_tarihi=kiosk.olusturulma_tarihi,
        ))
    Atama.objects.using(db).bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [
        ("pharmacies", "0010_kiosk_eczane_kiosk_no"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="KioskEczaneAtama",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("olusturulma_tarihi", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("guncellenme_tarihi", models.DateTimeField(auto_now_add=True)),
                ("surum", models.PositiveIntegerField(default=1, editable=False)),
                ("baslangic_zamani", models.DateTimeField(db_index=True)),
                ("bitis_zamani", models.DateTimeField(null=True, blank=True, db_index=True)),
                ("tasima_nedeni", models.CharField(max_length=250, blank=True, default="")),
                ("eczane", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="kiosk_atamalari", to="pharmacies.eczane")),
                ("kiosk", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="eczane_atamalari", to="pharmacies.kiosk")),
                ("tasiyan_admin", models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name="kiosk_tasimalari", to=settings.AUTH_USER_MODEL)),
                ("olusturan", models.ForeignKey(null=True, blank=True, editable=False, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("guncelleyen", models.ForeignKey(null=True, blank=True, editable=False, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "kiosk_eczane_atamalari", "ordering": ("-baslangic_zamani", "-id")},
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="kioskeczaneatama",
            constraint=models.UniqueConstraint(fields=["kiosk"], condition=models.Q(bitis_zamani__isnull=True), name="uniq_kiosk_acik_eczane_atamasi"),
        ),
        migrations.AddConstraint(
            model_name="kioskeczaneatama",
            constraint=models.CheckConstraint(condition=models.Q(bitis_zamani__isnull=True) | models.Q(bitis_zamani__gte=models.F("baslangic_zamani")), name="kiosk_atama_bitis_baslangic_sirasi"),
        ),
    ]
