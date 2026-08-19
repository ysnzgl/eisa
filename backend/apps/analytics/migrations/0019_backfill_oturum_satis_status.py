from django.db import migrations
from django.db.models.functions import Coalesce


def forwards(apps, schema_editor):
    OturumLogu = apps.get_model("analytics", "OturumLogu")
    OturumLogu.objects.filter(sold__isnull=True).update(status=0)
    OturumLogu.objects.filter(sold=True).update(status=2)
    OturumLogu.objects.filter(sold=False).update(status=3)
    OturumLogu.objects.filter(sold__isnull=False).update(
        result_at=Coalesce("danisma_tamamlanma_tarihi", "olusturulma_tarihi")
    )


def backwards(apps, schema_editor):
    OturumLogu = apps.get_model("analytics", "OturumLogu")
    OturumLogu.objects.filter(status__in=(0, 1)).update(sold=None)
    OturumLogu.objects.filter(status=2).update(sold=True)
    OturumLogu.objects.filter(status=3).update(sold=False)


class Migration(migrations.Migration):
    dependencies = [("analytics", "0018_oturum_satis_status")]
    operations = [migrations.RunPython(forwards, backwards)]
