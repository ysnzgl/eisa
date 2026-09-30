from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pharmacies", "0015_kiosk_idle_audio_schedule")]

    operations = [
        migrations.AddField(
            model_name="kiosk",
            name="kiosk_build_number",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Kiosk edge'in merkeziye bildirdigi anlasilir build/surum numarasi.",
                max_length=64,
            ),
        ),
    ]
