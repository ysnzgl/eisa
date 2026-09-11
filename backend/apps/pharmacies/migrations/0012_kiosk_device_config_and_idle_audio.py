from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("pharmacies", "0011_kiosk_eczane_atama")]

    operations = [
        migrations.AddField(model_name="kiosk", name="interaction_timeout_seconds", field=models.PositiveIntegerField(default=20, help_text="Etkilesim ekranlarinda islemsizlik sonrasi idle'a donus suresi.")),
        migrations.AddField(model_name="kiosk", name="idle_content_min_seconds", field=models.PositiveIntegerField(default=10, help_text="Idle metin icerigi icin minimum gosterim suresi.")),
        migrations.AddField(model_name="kiosk", name="idle_content_max_seconds", field=models.PositiveIntegerField(default=12, help_text="Idle metin icerigi icin maksimum gosterim suresi.")),
        migrations.AddField(model_name="kiosk", name="idle_content_refresh_seconds", field=models.PositiveIntegerField(default=300, help_text="Lokal UI'nin idle icerik/config yenileme suresi.")),
        migrations.AddField(model_name="kiosk", name="idle_audio_delay_seconds", field=models.PositiveIntegerField(default=1200, help_text="Kesintisiz idle durumunda sesin baslamasi icin beklenecek sure.")),
        migrations.AddField(model_name="kiosk", name="idle_audio_enabled", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="kiosk", name="idle_audio_media_url", field=models.URLField(blank=True, default="", max_length=1000)),
        migrations.AddField(model_name="kiosk", name="idle_audio_object_key", field=models.CharField(blank=True, default="", max_length=500)),
        migrations.AddField(model_name="kiosk", name="idle_audio_checksum", field=models.CharField(blank=True, default="", max_length=80)),
        migrations.AddField(model_name="kiosk", name="idle_audio_original_name", field=models.CharField(blank=True, default="", max_length=255)),
        migrations.AddField(model_name="kiosk", name="idle_audio_content_type", field=models.CharField(blank=True, default="", max_length=100)),
    ]
