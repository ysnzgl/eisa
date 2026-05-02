from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="icon",
            field=models.CharField(default="fa-circle", max_length=64),
        ),
        migrations.AddField(
            model_name="question",
            name="seed_id",
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="question",
            name="match_rules",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
