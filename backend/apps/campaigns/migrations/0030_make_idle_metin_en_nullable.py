from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0029_idlescreencontent_english"),
    ]

    operations = [
        migrations.AlterField(
            model_name="idlescreencontent",
            name="metin_en",
            field=models.CharField(
                max_length=1000,
                null=True,
                blank=True,
                default="",
                help_text="Ingilizce idle metni. Bos = kioskta Turkce metne geri doner.",
            ),
        ),
    ]
