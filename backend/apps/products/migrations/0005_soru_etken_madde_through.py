"""
hedef_etken_maddeler M2M → through model SoruEtkenMadde ile değiştirildi.
SoruEtkenMadde: soru, etken_madde, rol alanları + unique_together(soru, etken_madde).
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_refactor_hedefleme'),
    ]

    operations = [
        # ── Eski basit M2M kaldır ──────────────────────────────────────
        migrations.RemoveField(
            model_name='soru',
            name='hedef_etken_maddeler',
        ),

        # ── Through model tablosu oluştur ─────────────────────────────
        migrations.CreateModel(
            name='SoruEtkenMadde',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rol', models.CharField(
                    choices=[('ana', 'Ana'), ('destekleyici', 'Destekleyici')],
                    default='ana',
                    max_length=16,
                )),
                ('etken_madde', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='soru_baglantilari',
                    to='products.etkenmadde',
                )),
                ('soru', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='etken_madde_baglantilari',
                    to='products.soru',
                )),
            ],
            options={
                'verbose_name': 'Soru Etken Madde',
                'verbose_name_plural': 'Soru Etken Maddeler',
                'db_table': 'soru_etken_maddeler',
                'unique_together': {('soru', 'etken_madde')},
            },
        ),

        # ── M2M'i through model ile yeniden ekle ─────────────────────
        migrations.AddField(
            model_name='soru',
            name='hedef_etken_maddeler',
            field=models.ManyToManyField(
                blank=True,
                help_text='Bos = herkese goster.',
                related_name='hedef_sorular',
                through='products.SoruEtkenMadde',
                to='products.etkenmadde',
            ),
        ),
    ]
