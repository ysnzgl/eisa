from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pharmacies", "0016_kiosk_build_number")]

    operations = [
        migrations.AddField(
            model_name="kiosk",
            name="idle_audio_countdown_visible",
            field=models.BooleanField(
                default=False,
                help_text="Idle ses geri sayiminin kiosk ekraninda gorunup gorunmeyecegi.",
            ),
        ),
    ]
