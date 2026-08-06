"""Kiosk modeline eczane_kiosk_no (1-31, eczane-unique) alanı eklendi.

Backfill: Mevcut kiosklar eczane bazında id sıralamasıyla 1'den başlayan
stabil numara alır. 31'i aşan kiosklu eczaneler için overflow kiosklar
NULL bırakılır (bu durumda kiosk QR üretemez; admin yeniden atamalıdır).
"""
from django.db import migrations, models


def backfill_eczane_kiosk_no(apps, schema_editor):
    Kiosk = apps.get_model('pharmacies', 'Kiosk')
    db_alias = schema_editor.connection.alias

    from django.db import connections
    conn = connections[db_alias]
    vendor = conn.vendor  # 'postgresql' | 'sqlite'

    if vendor == 'postgresql':
        # Tek sorguda ROW_NUMBER ile ata; 31 üstü NULL kalır.
        schema_editor.execute("""
            WITH ranked AS (
                SELECT id,
                       ROW_NUMBER() OVER (PARTITION BY eczane_id ORDER BY id) AS rn
                FROM kiosklar
            )
            UPDATE kiosklar
               SET eczane_kiosk_no = ranked.rn
              FROM ranked
             WHERE kiosklar.id = ranked.id
               AND ranked.rn <= 31
        """)
    else:
        # SQLite: Python döngüsüyle eczane başına sırala
        from collections import defaultdict
        buckets = defaultdict(list)
        for k in Kiosk.objects.using(db_alias).order_by('eczane_id', 'id').values('id', 'eczane_id'):
            buckets[k['eczane_id']].append(k['id'])
        for eczane_id, kiosk_ids in buckets.items():
            for slot, kiosk_id in enumerate(kiosk_ids, start=1):
                if slot > 31:
                    break
                Kiosk.objects.using(db_alias).filter(pk=kiosk_id).update(eczane_kiosk_no=slot)


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacies', '0009_kiosk_last_ip'),
    ]

    operations = [
        migrations.AddField(
            model_name='kiosk',
            name='eczane_kiosk_no',
            field=models.PositiveSmallIntegerField(
                null=True, blank=True,
                help_text='Eczane içindeki stabil kiosk sıra numarası (1-31). Crockford QR prefix\'i.',
            ),
        ),
        migrations.RunPython(backfill_eczane_kiosk_no, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='kiosk',
            constraint=models.UniqueConstraint(
                fields=['eczane', 'eczane_kiosk_no'],
                condition=models.Q(eczane_kiosk_no__isnull=False),
                name='uniq_kiosk_eczane_no',
            ),
        ),
        migrations.AddConstraint(
            model_name='kiosk',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(eczane_kiosk_no__isnull=True)
                    | (models.Q(eczane_kiosk_no__gte=1) & models.Q(eczane_kiosk_no__lte=31))
                ),
                name='kiosk_eczane_no_range',
            ),
        ),
    ]
