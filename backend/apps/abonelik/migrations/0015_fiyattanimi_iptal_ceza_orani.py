from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("abonelik", "0014_sozlesme_onayli_sozlesme_metni"),
    ]

    operations = [
        migrations.AddField(
            model_name="fiyattanimi",
            name="iptal_ceza_orani",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("2.00"),
                help_text="Erken iptal ceza katsayısı: ceza = kalan_ay × katsayi × aylık_bedel.",
                max_digits=5,
            ),
        ),
    ]
