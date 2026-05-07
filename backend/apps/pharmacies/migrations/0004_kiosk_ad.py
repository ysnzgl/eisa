"""Kiosk tablosuna zorunlu ad alani eklendi."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacies', '0003_eczane_telefon_kod'),
    ]

    operations = [
        migrations.AddField(
            model_name='kiosk',
            name='ad',
            field=models.CharField(default='Kiosk', max_length=50),
            preserve_default=False,
        ),
    ]
