"""Reklam modeline musteri, sure_saniye, yayin_baslangic, yayin_bitis alanları eklendi."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0003_reklam_hedefleme_revize"),
    ]

    operations = [
        migrations.AddField(
            model_name="reklam",
            name="musteri",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="reklam",
            name="sure_saniye",
            field=models.PositiveSmallIntegerField(default=15),
        ),
        migrations.AddField(
            model_name="reklam",
            name="yayin_baslangic",
            field=models.TimeField(
                blank=True,
                help_text="Günlük yayın başlangıç saati",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="reklam",
            name="yayin_bitis",
            field=models.TimeField(
                blank=True,
                help_text="Günlük yayın bitiş saati",
                null=True,
            ),
        ),
    ]
