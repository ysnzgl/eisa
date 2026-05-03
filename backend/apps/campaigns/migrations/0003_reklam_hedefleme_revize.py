"""
Reklam hedefleme revize:
- Eski: hedef_iller, hedef_ilceler, hedef_yas_araliklari, hedef_cinsiyetler (lookup M2M)
- Yeni: hedef_eczaneler (pharmacies.Eczane M2M)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0002_initial'),
        ('pharmacies', '0002_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reklam',
            name='hedef_cinsiyetler',
        ),
        migrations.RemoveField(
            model_name='reklam',
            name='hedef_ilceler',
        ),
        migrations.RemoveField(
            model_name='reklam',
            name='hedef_iller',
        ),
        migrations.RemoveField(
            model_name='reklam',
            name='hedef_yas_araliklari',
        ),
        migrations.AddField(
            model_name='reklam',
            name='hedef_eczaneler',
            field=models.ManyToManyField(
                blank=True,
                related_name='reklamlar',
                to='pharmacies.eczane',
            ),
        ),
    ]
