from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0013_add_english_translations"),
    ]

    operations = [
        migrations.AlterField(
            model_name="soru",
            name="metin_en",
            field=models.TextField(
                null=True,
                blank=True,
                default="",
                help_text="Ingilizce soru metni. Bos = kioskta Turkce metne geri doner.",
            ),
        ),
        migrations.AlterField(
            model_name="cevap",
            name="metin_en",
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                default="",
                help_text="Ingilizce cevap metni. Bos = kioskta Turkce metne geri doner.",
            ),
        ),
    ]
