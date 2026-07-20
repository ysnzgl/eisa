# 2026-07-20 — Add unique constraint + enforce max_length=8 on qr_kodu.
#
# Depends on 0007_qr_data_cleanup which guarantees:
#   - No empty values
#   - All values are exactly 8 chars [A-Z0-9]
#   - No duplicates
#
# PostgreSQL: reducing varchar length requires all existing values to fit.
# After 0007, all values are exactly 8 chars — safe to apply max_length=8.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0007_oturumcevap_guncelleyen_oturumcevap_olusturan_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oturumlogu',
            name='qr_kodu',
            field=models.CharField(db_index=True, max_length=8, unique=True),
        ),
    ]
