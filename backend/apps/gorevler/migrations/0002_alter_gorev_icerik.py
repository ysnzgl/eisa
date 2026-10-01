from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gorevler", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gorev",
            name="icerik",
            field=models.TextField(),
        ),
    ]
