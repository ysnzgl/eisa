"""Lookup tohumlama icin yardimcilar."""
from __future__ import annotations

from .models import Cinsiyet, Il, Ilce, YasAraligi


CINSIYET_SEED = [
    {"kod": "F", "ad": "Kadin"},
    {"kod": "M", "ad": "Erkek"},
    {"kod": "O", "ad": "Diger"},
]

YAS_ARALIGI_SEED = [
    {"kod": "0-17", "ad": "0-17", "alt_sinir": 0, "ust_sinir": 17},
    {"kod": "18-25", "ad": "18-25", "alt_sinir": 18, "ust_sinir": 25},
    {"kod": "26-35", "ad": "26-35", "alt_sinir": 26, "ust_sinir": 35},
    {"kod": "36-50", "ad": "36-50", "alt_sinir": 36, "ust_sinir": 50},
    {"kod": "51-65", "ad": "51-65", "alt_sinir": 51, "ust_sinir": 65},
    {"kod": "65+", "ad": "65+", "alt_sinir": 65, "ust_sinir": None},
]

# Hizli demo verisi icin minik il/ilce ornek seti.
IL_ILCE_SEED = {
    "Istanbul": ["Kadikoy", "Besiktas", "Sisli", "Uskudar", "Bakirkoy", "Atasehir"],
    "Ankara": ["Cankaya", "Kecioren", "Mamak", "Yenimahalle"],
    "Izmir": ["Konak", "Bornova", "Karsiyaka", "Buca"],
    "Bursa": ["Osmangazi", "Nilufer", "Yildirim"],
    "Antalya": ["Muratpasa", "Konyaalti", "Kepez"],
}


def seed_lookups() -> dict:
    """Tum lookup tablolarini idempotent sekilde tohumlar."""
    counts = {"cinsiyet": 0, "yas_araligi": 0, "il": 0, "ilce": 0}

    for item in CINSIYET_SEED:
        _, c = Cinsiyet.objects.get_or_create(kod=item["kod"], defaults=item)
        counts["cinsiyet"] += int(c)

    for item in YAS_ARALIGI_SEED:
        _, c = YasAraligi.objects.get_or_create(kod=item["kod"], defaults=item)
        counts["yas_araligi"] += int(c)

    for il_ad, ilceler in IL_ILCE_SEED.items():
        il, c = Il.objects.get_or_create(ad=il_ad)
        counts["il"] += int(c)
        for ilce_ad in ilceler:
            _, c2 = Ilce.objects.get_or_create(il=il, ad=ilce_ad)
            counts["ilce"] += int(c2)

    return counts
