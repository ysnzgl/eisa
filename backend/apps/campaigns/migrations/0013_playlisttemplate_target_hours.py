from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0012_campaign_is_guaranteed_campaign_priority_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="playlisttemplate",
            name="target_hours",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Bu sablonun aktif oldugu saat dilimleri (0-23). Bos = herhangi bir saat kurali tanimlanmamis.",
            ),
        ),
    ]
