"""
Creative modeline active_media_url eklendi.

Additive, geriye uyumlu migration.
- Eski creative kayıtları: active_media_url='' (boş) ile çalışmaya devam eder.
- AdStrip fallback: boşsa bekleme görseli (object-fit: contain) kullanılır.
"""
from django.db import migrations, models
import apps.campaigns.models


class Migration(migrations.Migration):

    dependencies = [
        ("campaigns", "0020_faz7_drop_deprecated_campaign_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="creative",
            name="active_media_url",
            field=models.URLField(
                blank=True,
                default="",
                max_length=2048,
                validators=[apps.campaigns.models._https_url_validator],
                help_text=(
                    "Islem ekrani alt alani icin medya URL'i (~1080x768, yaklasik 7:5). "
                    "Bos birakılırsa AdStrip'te bekleme ekrani gorseli fallback olarak kullanilir."
                ),
            ),
        ),
    ]
