"""Lookup tohumlama icin yardimcilar."""
from __future__ import annotations

from .models import Cinsiyet, YasAraligi


CINSIYET_SEED = [
    {"kod": "F", "ad": "Kadin"},
    {"kod": "M", "ad": "Erkek"},
]

YAS_ARALIGI_SEED = [
    {"kod": "0-17", "ad": "0-17", "alt_sinir": 0, "ust_sinir": 17},
    {"kod": "18-25", "ad": "18-25", "alt_sinir": 18, "ust_sinir": 25},
    {"kod": "26-35", "ad": "26-35", "alt_sinir": 26, "ust_sinir": 35},
    {"kod": "36-50", "ad": "36-50", "alt_sinir": 36, "ust_sinir": 50},
    {"kod": "51-65", "ad": "51-65", "alt_sinir": 51, "ust_sinir": 65},
    {"kod": "65+", "ad": "65+", "alt_sinir": 65, "ust_sinir": None},
]




def seed_lookups() -> dict:
    """Tum lookup tablolarini idempotent sekilde tohumlar."""
    counts = {"cinsiyet": 0, "yas_araligi": 0}

    for item in CINSIYET_SEED:
        _, c = Cinsiyet.objects.get_or_create(kod=item["kod"], defaults=item)
        counts["cinsiyet"] += int(c)

    for item in YAS_ARALIGI_SEED:
        _, c = YasAraligi.objects.get_or_create(kod=item["kod"], defaults=item)
        counts["yas_araligi"] += int(c)

   

    return counts
