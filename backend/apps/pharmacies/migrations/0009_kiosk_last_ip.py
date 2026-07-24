"""Kiosk tablosuna last_ip (son ping IP adresi) alanı eklendi."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacies', '0008_faz4_faz5_kiosk_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='kiosk',
            name='last_ip',
            field=models.GenericIPAddressField(
                null=True, blank=True,
                help_text="Son ping'de tespit edilen kiosk IP adresi.",
            ),
        ),
    ]
