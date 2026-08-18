from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0014_oturumlogu_barkod_logo"),
    ]

    operations = [
        migrations.AddField(
            model_name="oturumlogu",
            name="satis_sonucu",
            field=models.CharField(
                blank=True,
                choices=[("sold", "Satış yapıldı"), ("not_sold", "Satış yapılmadı")],
                max_length=16,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="oturumlogu",
            name="satis_edilen_etken_maddeler",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
