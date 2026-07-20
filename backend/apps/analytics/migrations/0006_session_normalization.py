# 2026-07-20 — Schema expansion (no qr_kodu unique constraint here; that comes in 0008
# after the data-cleanup migration 0007 ensures all values are valid 8-char codes).
#
# Split rationale:
#   0006 — additive schema changes only (safe to apply on production with data)
#   0007 — RunPython data migration (clean invalid/duplicate QR values)
#   0008 — AlterField adds unique=True + max_length=8 (safe once 0007 ran)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0005_oturumlogu_danisma_notu_and_more'),
        ('products', '0011_alter_danisma_ad_alter_kategori_ad'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Add oturum_tipi
        migrations.AddField(
            model_name='oturumlogu',
            name='oturum_tipi',
            field=models.CharField(
                choices=[('SIKAYET', 'Sikayet'), ('OZEL_DANISMANLIK', 'Ozel Danismanlik')],
                db_index=True,
                default='SIKAYET',
                help_text='Akis turu: sikayet (etken madde onerisi) veya ozel danismanlik.',
                max_length=16,
            ),
        ),
        # 2. Add danisma_kategorisi FK (nullable)
        migrations.AddField(
            model_name='oturumlogu',
            name='danisma_kategorisi',
            field=models.ForeignKey(
                blank=True,
                help_text='Ozel danismanlik oturumu icin konu (oturum_tipi=OZEL_DANISMANLIK ise zorunlu).',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='oturumlar',
                to='products.danisma',
            ),
        ),
        # 3. Make kategori nullable (consultation sessions have no product category)
        migrations.AlterField(
            model_name='oturumlogu',
            name='kategori',
            field=models.ForeignKey(
                blank=True,
                help_text='Sikayet akisi icin kategori (oturum_tipi=SIKAYET ise zorunlu).',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='oturumlar',
                to='products.kategori',
            ),
        ),
        # 4. Create OturumCevap — all BaseModel fields included correctly from the start
        migrations.CreateModel(
            name='OturumCevap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('olusturulma_tarihi', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('guncellenme_tarihi', models.DateTimeField(auto_now_add=True)),
                ('surum', models.PositiveIntegerField(default=1, editable=False)),
                ('soru_metni_snapshot', models.CharField(blank=True, max_length=500)),
                ('cevap_metni_snapshot', models.CharField(blank=True, max_length=500)),
                ('cevap_degeri_snapshot', models.CharField(blank=True, help_text='Eski format uyumlu (Y/N/diger).', max_length=100)),
                ('olusturan', models.ForeignKey(
                    blank=True, editable=False, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to=settings.AUTH_USER_MODEL,
                )),
                ('guncelleyen', models.ForeignKey(
                    blank=True, editable=False, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to=settings.AUTH_USER_MODEL,
                )),
                ('cevap', models.ForeignKey(
                    blank=True, null=True,
                    help_text='Cevap referansi (silindiginde null). Snapshot alanlar korunur.',
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='oturum_secilimleri', to='products.cevap',
                )),
                ('oturum', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cevap_detaylari', to='analytics.oturumlogu',
                )),
                ('soru', models.ForeignKey(
                    blank=True, null=True,
                    help_text='Soru referansi (silindiginde null). Snapshot alanlar korunur.',
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='oturum_cevaplari', to='products.soru',
                )),
            ],
            options={
                'verbose_name': 'Oturum Cevap',
                'verbose_name_plural': 'Oturum Cevaplar',
                'db_table': 'oturum_cevaplar',
                'ordering': ('oturum_id', 'id'),
                'unique_together': {('oturum', 'soru')},
            },
        ),
        # 5. Create OturumOnerilenEtkenMadde — all BaseModel fields included correctly
        migrations.CreateModel(
            name='OturumOnerilenEtkenMadde',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('olusturulma_tarihi', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('guncellenme_tarihi', models.DateTimeField(auto_now_add=True)),
                ('surum', models.PositiveIntegerField(default=1, editable=False)),
                ('etken_madde_adi_snapshot', models.CharField(blank=True, max_length=250)),
                ('olusturan', models.ForeignKey(
                    blank=True, editable=False, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to=settings.AUTH_USER_MODEL,
                )),
                ('guncelleyen', models.ForeignKey(
                    blank=True, editable=False, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='+', to=settings.AUTH_USER_MODEL,
                )),
                ('etken_madde', models.ForeignKey(
                    blank=True, null=True,
                    help_text='Etken madde referansi (silindiginde null). Snapshot korunur.',
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='oneri_kayitlari', to='products.etkenmadde',
                )),
                ('oturum', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='onerilen_etken_madde_detaylari', to='analytics.oturumlogu',
                )),
            ],
            options={
                'verbose_name': 'Oturum Onerilen Etken Madde',
                'verbose_name_plural': 'Oturum Onerilen Etken Maddeler',
                'db_table': 'oturum_onerilen_etken_maddeler',
                'ordering': ('oturum_id', 'id'),
                'unique_together': {('oturum', 'etken_madde')},
            },
        ),
    ]
