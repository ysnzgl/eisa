from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pharmacies", "0014_kiosk_audio_library")]

    operations = [
        migrations.AddField(
            model_name="kiosk",
            name="idle_audio_schedule_mode",
            field=models.CharField(
                choices=[("BUSINESS_HOURS", "Mesai ici (08:00-19:00)"), ("ALL_DAY", "24 saat")],
                default="ALL_DAY", help_text="Idle sesin normal gunlerde calacagi zaman araligi.", max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="kiosk",
            name="idle_audio_play_on_duty",
            field=models.BooleanField(default=False, help_text="Nobet gunlerinde mesai saati kisitini kaldirir."),
        ),
    ]
