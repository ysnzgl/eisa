from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analytics", "0015_oturumlogu_satis_fields"),
    ]

    operations = [
        # OturumOnerilenEtkenMadde: satildi flag
        migrations.AddField(
            model_name="oturumonerilenetkenmadde",
            name="satildi",
            field=models.BooleanField(default=False),
        ),
        # OturumLogu: drop satis_sonucu + satis_edilen_etken_maddeler, add sold
        migrations.RemoveField(model_name="oturumlogu", name="satis_sonucu"),
        migrations.RemoveField(model_name="oturumlogu", name="satis_edilen_etken_maddeler"),
        migrations.AddField(
            model_name="oturumlogu",
            name="sold",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
