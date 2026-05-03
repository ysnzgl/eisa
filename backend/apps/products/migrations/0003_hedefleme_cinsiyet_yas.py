"""
Kategori ve Soru modeline cinsiyet/yas hedefleme M2M eklendi.
Bos = herkese goster.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_initial'),
        ('lookups', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='kategori',
            name='hedef_cinsiyetler',
            field=models.ManyToManyField(
                blank=True,
                help_text='Bos = herkese goster.',
                related_name='hedef_kategoriler',
                to='lookups.cinsiyet',
            ),
        ),
        migrations.AddField(
            model_name='kategori',
            name='hedef_yas_araliklari',
            field=models.ManyToManyField(
                blank=True,
                help_text='Bos = herkese goster.',
                related_name='hedef_kategoriler',
                to='lookups.yasaraligi',
            ),
        ),
        migrations.AddField(
            model_name='soru',
            name='hedef_cinsiyetler',
            field=models.ManyToManyField(
                blank=True,
                help_text='Bos = herkese goster.',
                related_name='hedef_sorular',
                to='lookups.cinsiyet',
            ),
        ),
        migrations.AddField(
            model_name='soru',
            name='hedef_yas_araliklari',
            field=models.ManyToManyField(
                blank=True,
                help_text='Bos = herkese goster.',
                related_name='hedef_sorular',
                to='lookups.yasaraligi',
            ),
        ),
    ]
