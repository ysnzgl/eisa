# Data migration — başlangıç destek parametreleri (idempotent)
from django.db import migrations


def _seed(apps, schema_editor):
    DestekParametresi = apps.get_model("destek", "DestekParametresi")

    for p in [
        {"kod": "ONERI",   "ad": "Öneri",   "sira": 1},
        {"kod": "SIKAYET", "ad": "Şikayet", "sira": 2},
    ]:
        DestekParametresi.objects.get_or_create(
            kod=p["kod"],
            defaults={"grup": "TALEP_TURU", "ad": p["ad"], "sira": p["sira"], "aktif": True},
        )

    for p in [
        {"kod": "KIOSK",  "ad": "Kiosk",  "sira": 1},
        {"kod": "PORTAL", "ad": "Portal", "sira": 2},
    ]:
        DestekParametresi.objects.get_or_create(
            kod=p["kod"],
            defaults={"grup": "ALAN", "ad": p["ad"], "sira": p["sira"], "aktif": True},
        )

    kiosk_alan  = DestekParametresi.objects.get(kod="KIOSK")
    portal_alan = DestekParametresi.objects.get(kod="PORTAL")

    for p in [
        {"kod": "KIOSK_CIHAZ",         "ad": "Cihaz",         "sira": 1},
        {"kod": "KIOSK_SORU",          "ad": "Soru",          "sira": 2},
        {"kod": "KIOSK_ONERILEN_URUN", "ad": "Önerilen Ürün", "sira": 3},
        {"kod": "KIOSK_SPONSORLUK",    "ad": "Sponsorluk",    "sira": 4},
        {"kod": "KIOSK_DIGER",         "ad": "Diğer",         "sira": 5},
    ]:
        DestekParametresi.objects.get_or_create(
            kod=p["kod"],
            defaults={"grup": "ALT_KONU", "ad": p["ad"], "sira": p["sira"],
                      "ust_parametre": kiosk_alan, "aktif": True},
        )

    for p in [
        {"kod": "PORTAL_DASHBOARD",      "ad": "Dashboard",        "sira": 1},
        {"kod": "PORTAL_QR_BASVURU",     "ad": "QR / Başvuru",     "sira": 2},
        {"kod": "PORTAL_SPONSORLUK",     "ad": "Sponsorluk",       "sira": 3},
        {"kod": "PORTAL_HESAP_KULLANIM", "ad": "Hesap / Kullanım", "sira": 4},
        {"kod": "PORTAL_DIGER",          "ad": "Diğer",            "sira": 5},
    ]:
        DestekParametresi.objects.get_or_create(
            kod=p["kod"],
            defaults={"grup": "ALT_KONU", "ad": p["ad"], "sira": p["sira"],
                      "ust_parametre": portal_alan, "aktif": True},
        )

    for p in [
        {"kod": "YENI",        "ad": "Yeni",        "sira": 1},
        {"kod": "INCELENIYOR", "ad": "İnceleniyor", "sira": 2},
        {"kod": "YANITLANDI",  "ad": "Yanıtlandı",  "sira": 3},
        {"kod": "KAPATILDI",   "ad": "Kapatıldı",   "sira": 4},
    ]:
        DestekParametresi.objects.get_or_create(
            kod=p["kod"],
            defaults={"grup": "DURUM", "ad": p["ad"], "sira": p["sira"], "aktif": True},
        )


def _reverse(apps, schema_editor):
    pass  # Seed geri alınmaz.


class Migration(migrations.Migration):

    dependencies = [
        ("destek", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_seed, _reverse),
    ]
