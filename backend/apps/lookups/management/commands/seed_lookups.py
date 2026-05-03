"""python manage.py seed_lookups — Sabit tablolari tohumlar."""
from django.core.management.base import BaseCommand

from apps.lookups.seed import seed_lookups


class Command(BaseCommand):
    help = "Lookup tablolarini (Il, Ilce, Cinsiyet, YasAraligi) idempotent tohumlar."

    def handle(self, *args, **options):
        counts = seed_lookups()
        self.stdout.write(self.style.SUCCESS(
            f"Lookup tohumlama tamamlandi: "
            f"il+{counts['il']}, ilce+{counts['ilce']}, "
            f"cinsiyet+{counts['cinsiyet']}, yas_araligi+{counts['yas_araligi']}"
        ))
