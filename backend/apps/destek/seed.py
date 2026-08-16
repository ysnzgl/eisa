"""Destek başlangıç parametrelerini idempotent biçimde ekler.

Hem data migration hem de test fixture tarafından kullanılır.
"""
from apps.destek.models import DestekParametresi


def seed_destek_parametreleri():
    """Aktif olmayan parametreleri oluşturur veya günceller (idempotent)."""

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
