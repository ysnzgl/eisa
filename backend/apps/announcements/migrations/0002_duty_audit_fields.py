from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("announcements", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(model_name="pharmacydutymonth", name="olusturulma_tarihi", field=models.DateTimeField(auto_now_add=True, db_index=True, default=django.utils.timezone.now), preserve_default=False),
        migrations.AddField(model_name="pharmacydutymonth", name="guncellenme_tarihi", field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now), preserve_default=False),
        migrations.AddField(model_name="pharmacydutymonth", name="surum", field=models.PositiveIntegerField(default=1, editable=False)),
        migrations.AddField(model_name="pharmacydutymonth", name="olusturan", field=models.ForeignKey(null=True, blank=True, editable=False, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="pharmacydutymonth", name="guncelleyen", field=models.ForeignKey(null=True, blank=True, editable=False, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="pharmacydutyday", name="olusturulma_tarihi", field=models.DateTimeField(auto_now_add=True, db_index=True, default=django.utils.timezone.now), preserve_default=False),
        migrations.AddField(model_name="pharmacydutyday", name="guncellenme_tarihi", field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now), preserve_default=False),
        migrations.AddField(model_name="pharmacydutyday", name="surum", field=models.PositiveIntegerField(default=1, editable=False)),
        migrations.AddField(model_name="pharmacydutyday", name="olusturan", field=models.ForeignKey(null=True, blank=True, editable=False, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="pharmacydutyday", name="guncelleyen", field=models.ForeignKey(null=True, blank=True, editable=False, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
    ]
