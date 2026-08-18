"""Offline-first QR — OturumLogu şema değişiklikleri.

1. eczane FK eklendi (nullable, SET_NULL).
2. qr_kodu: max_length 8→9, nullable, global unique constraint kaldırıldı.
3. Eczane-scoped conditional unique constraint eklendi:
   UNIQUE(eczane_id, qr_kodu) WHERE qr_kodu IS NOT NULL
4. Backfill: mevcut kayıtlar için eczane_id = kiosk.eczane_id.
   Kioski olmayan (silinmiş) kayıtlar NULL bırakılır.
"""
from django.db import migrations, models
import django.db.models.deletion


def backfill_eczane(apps, schema_editor):
    """Mevcut oturumlar için eczane_id = kiosk.eczane_id."""
    db = schema_editor.connection.alias
    vendor = schema_editor.connection.vendor

    if vendor == 'postgresql':
        schema_editor.execute("""
            UPDATE oturum_loglari ol
               SET eczane_id = k.eczane_id
              FROM kiosklar k
             WHERE ol.kiosk_id = k.id
               AND ol.eczane_id IS NULL
        """)
    else:
        # SQLite: güvenli Python döngüsü
        OturumLogu = apps.get_model('analytics', 'OturumLogu')
        Kiosk = apps.get_model('pharmacies', 'Kiosk')
        kiosk_eczane = {k.pk: k.eczane_id for k in Kiosk.objects.using(db).all()}
        batch = []
        for oturum in OturumLogu.objects.using(db).filter(eczane__isnull=True).iterator(chunk_size=500):
            eczane_id = kiosk_eczane.get(oturum.kiosk_id)
            if eczane_id:
                oturum.eczane_id = eczane_id
                batch.append(oturum)
            if len(batch) >= 500:
                OturumLogu.objects.using(db).bulk_update(batch, ['eczane_id'])
                batch = []
        if batch:
            OturumLogu.objects.using(db).bulk_update(batch, ['eczane_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0011_faz4_kiosk_event'),
        ('pharmacies', '0010_kiosk_eczane_kiosk_no'),
    ]

    operations = [
        # 1. eczane FK ekle (nullable)
        migrations.AddField(
            model_name='oturumlogu',
            name='eczane',
            field=django.db.models.fields.related.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='oturumlar',
                to='pharmacies.eczane',
                help_text='Oturumun kaydedildiği eczane. Kiosk payload\'ından alınmaz; auth context\'ten atanır.',
            ),
        ),
        # 2. qr_kodu: nullable, max_length=9, global unique kaldır
        migrations.AlterField(
            model_name='oturumlogu',
            name='qr_kodu',
            field=models.CharField(
                max_length=9,
                null=True,
                blank=True,
                db_index=True,
                help_text='9 karakter Crockford (yeni) veya 8 karakter legacy. Null: terk edilmiş oturum.',
            ),
        ),
        # 3. Mevcut kayıtlar için eczane backfill
        migrations.RunPython(backfill_eczane, migrations.RunPython.noop),
        # 4. Eczane-scoped conditional unique constraint
        migrations.AddConstraint(
            model_name='oturumlogu',
            constraint=models.UniqueConstraint(
                fields=['eczane', 'qr_kodu'],
                condition=models.Q(qr_kodu__isnull=False),
                name='uniq_oturum_eczane_qr',
            ),
        ),
    ]
