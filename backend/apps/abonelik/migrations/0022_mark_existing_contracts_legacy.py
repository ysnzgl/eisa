from django.db import migrations


def mark_existing_contracts_legacy(apps, schema_editor):
    # Bu migration çalıştığı anda veritabanında bulunan sözleşmeler eski
    # matbu/koşullarıyla kalır. Migration sonrası oluşan kayıtlar model varsayılanı
    # olan 2026-EK1 sürümünü alır.
    Sozlesme = apps.get_model("abonelik", "Sozlesme")
    Sozlesme.objects.update(sozlesme_surumu="LEGACY")


class Migration(migrations.Migration):
    dependencies = [("abonelik", "0021_sozlesme_bolge_snapshot_sozlesme_ek2_islak_imza_url_and_more")]

    operations = [migrations.RunPython(mark_existing_contracts_legacy, migrations.RunPython.noop)]
