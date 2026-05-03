"""Eczane tablosuna telefon ve opsiyonel eczane_kodu alani eklendi."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacies', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='eczane',
            name='telefon',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='eczane',
            name='eczane_kodu',
            field=models.CharField(
                blank=True,
                help_text='Elle girilen eczane kodu (opsiyonel).',
                max_length=32,
                null=True,
                unique=True,
            ),
        ),
    ]
