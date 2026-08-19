from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("analytics", "0017_unique_etken_madde_snapshot")]
    operations = [
        migrations.AddField(
            model_name="oturumlogu",
            name="status",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "Bekliyor"), (1, "İncelendi"), (2, "Satış yapıldı"), (3, "Satış yapılmadı")],
                default=0,
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="oturumlogu",
            name="result_at",
            field=models.DateTimeField(null=True, blank=True, db_index=True),
        ),
    ]
