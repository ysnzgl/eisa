"""
hedef_cinsiyetler M2M → hedef_cinsiyet FK (tek sütun, opsiyonel).
Soru: seed_id ve eslesme_kurallari kaldırıldı.
Soru: hedef_etken_maddeler M2M eklendi.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_hedefleme_cinsiyet_yas'),
        ('lookups', '0001_initial'),
    ]

    operations = [
        # ── Soru: gereksiz alanları kaldır ──────────────────────────────
        migrations.RemoveField(model_name='soru', name='seed_id'),
        migrations.RemoveField(model_name='soru', name='eslesme_kurallari'),

        # ── M2M cinsiyet tabloları kaldır ────────────────────────────────
        migrations.RemoveField(model_name='kategori', name='hedef_cinsiyetler'),
        migrations.RemoveField(model_name='soru', name='hedef_cinsiyetler'),

        # ── Tek sütun FK ekle ────────────────────────────────────────────
        migrations.AddField(
            model_name='kategori',
            name='hedef_cinsiyet',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Bos = tum cinsiyetlere goster.',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='hedef_kategoriler',
                to='lookups.cinsiyet',
            ),
        ),
        migrations.AddField(
            model_name='soru',
            name='hedef_cinsiyet',
            field=models.ForeignKey(
                blank=True, null=True,
                help_text='Bos = tum cinsiyetlere goster.',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='hedef_sorular',
                to='lookups.cinsiyet',
            ),
        ),

        # ── Soru: hedef etken maddeler M2M ──────────────────────────────
        migrations.AddField(
            model_name='soru',
            name='hedef_etken_maddeler',
            field=models.ManyToManyField(
                blank=True,
                help_text='Bos = herkese goster.',
                related_name='hedef_sorular',
                to='products.etkenmadde',
            ),
        ),
    ]
