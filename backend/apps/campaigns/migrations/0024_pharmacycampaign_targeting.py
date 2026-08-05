"""
PharmacyCampaign: target_iller + target_ilceler M2M alanları eklendi.
duration_seconds default 10 → 15 olarak güncellendi.

Additive, geriye uyumlu migration.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0023_alter_pharmacycampaign_options_and_more"),
        ("lookups", "0002_remove_il_plaka"),
    ]

    operations = [
        # duration_seconds default değişikliği (data değişmez)
        migrations.AlterField(
            model_name="pharmacycampaign",
            name="duration_seconds",
            field=models.PositiveSmallIntegerField(
                default=15,
                help_text="Her döngüde gösterim süresi (saniye). İzin verilenler: 15, 30, 60.",
            ),
        ),
        # target_pharmacies help_text güncelle
        migrations.AlterField(
            model_name="pharmacycampaign",
            name="target_pharmacies",
            field=models.ManyToManyField(
                blank=True,
                help_text="Tekil hedef eczaneler.",
                related_name="pharmacy_campaigns",
                to="pharmacies.eczane",
            ),
        ),
        # target_iller M2M
        migrations.AddField(
            model_name="pharmacycampaign",
            name="target_iller",
            field=models.ManyToManyField(
                blank=True,
                help_text="Hedef iller (bu ile bağlı tüm eczaneleri kapsar).",
                related_name="pharmacy_campaigns",
                to="lookups.il",
            ),
        ),
        # target_ilceler M2M
        migrations.AddField(
            model_name="pharmacycampaign",
            name="target_ilceler",
            field=models.ManyToManyField(
                blank=True,
                help_text="Hedef ilçeler (bu ilçeye bağlı tüm eczaneleri kapsar).",
                related_name="pharmacy_campaigns",
                to="lookups.ilce",
            ),
        ),
    ]
