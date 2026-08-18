"""
Aynı oturuma null-FK etken maddenin snapshot adı üzerinden iki kez kaydedilmesini
engeller. FK mevcut olduğunda unique_together zaten koruyordu; bu constraint
yalnızca etken_madde IS NULL satırları kapsar.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0016_sold_and_satildi"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="oturumonerilenetkenmadde",
            constraint=models.UniqueConstraint(
                condition=models.Q(etken_madde__isnull=True),
                fields=["oturum", "etken_madde_adi_snapshot"],
                name="uniq_oturum_snapshot_null_fk",
            ),
        ),
    ]
