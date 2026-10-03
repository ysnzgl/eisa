from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gorevler", "0002_alter_gorev_icerik"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gorev",
            name="durum",
            field=models.CharField(
                choices=[
                    ("YENI", "Yeni"),
                    ("INCELENIYOR", "İnceleniyor"),
                    ("YAPILDI", "Yapıldı"),
                    ("YAPILMADI", "Yapılmadı"),
                    ("IPTAL", "İptal"),
                ],
                db_index=True,
                default="YENI",
                max_length=16,
            ),
        ),
    ]
