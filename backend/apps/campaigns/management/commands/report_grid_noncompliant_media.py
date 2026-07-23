"""Faz 1 — Grid uyumsuz medya raporu.

15sn planning grid (izin verilen: 15/30/45/60sn) ile uyumsuz
Creative ve HouseAd kayitlarini listeler. Hicbir degisiklik yapmaz.

Kullanim:
    python manage.py report_grid_noncompliant_media
    python manage.py report_grid_noncompliant_media --format csv
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.campaigns.models import Creative, HouseAd


GRID_DURATIONS = frozenset({15, 30, 45, 60})


class Command(BaseCommand):
    help = (
        "Faz 1: 15sn grid ile uyumsuz Creative ve HouseAd kayitlarini raporlar. "
        "Hicbir degisiklik yapmaz."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=["table", "csv"],
            default="table",
            help="Cikti formati (table | csv).",
        )

    def handle(self, *args, **options):
        fmt = options["format"]

        bad_creatives = [
            c for c in Creative.objects.select_related("campaign").order_by("campaign__name", "id")
            if int(c.duration_seconds) not in GRID_DURATIONS
        ]
        bad_house_ads = [
            h for h in HouseAd.objects.order_by("name", "id")
            if int(h.duration_seconds) not in GRID_DURATIONS
        ]

        total = len(bad_creatives) + len(bad_house_ads)

        if fmt == "csv":
            self.stdout.write("type,id,name,campaign,duration_seconds")
            for c in bad_creatives:
                self.stdout.write(
                    f"creative,{c.pk},{c.name},{c.campaign.name},{c.duration_seconds}"
                )
            for h in bad_house_ads:
                self.stdout.write(
                    f"house_ad,{h.pk},{h.name},,{h.duration_seconds}"
                )
        else:
            self.stdout.write(self.style.WARNING(
                f"\n=== Grid Uyumsuz Medya Raporu ===\n"
                f"  Izin verilen sureler: 15 / 30 / 45 / 60 saniye\n"
                f"  Toplam uyumsuz      : {total}\n"
            ))

            if bad_creatives:
                self.stdout.write(self.style.WARNING(
                    f"\n--- Uyumsuz Creative'ler ({len(bad_creatives)}) ---"
                ))
                for c in bad_creatives:
                    self.stdout.write(
                        f"  Creative pk={c.pk} | {c.duration_seconds}s"
                        f" | kampanya: {c.campaign.name}"
                        f" | {c.name or '(isimsiz)'}"
                    )
            else:
                self.stdout.write(self.style.SUCCESS(
                    "\n--- Creative: tum kayitlar grid uyumlu ---"
                ))

            if bad_house_ads:
                self.stdout.write(self.style.WARNING(
                    f"\n--- Uyumsuz HouseAd'ler ({len(bad_house_ads)}) ---"
                ))
                for h in bad_house_ads:
                    self.stdout.write(
                        f"  HouseAd pk={h.pk} | {h.duration_seconds}s | {h.name}"
                    )
            else:
                self.stdout.write(self.style.SUCCESS(
                    "\n--- HouseAd: tum kayitlar grid uyumlu ---"
                ))

            self.stdout.write(
                self.style.WARNING(
                    "\nNOT: Bu kayitlar V2 PlacementEngine (Faz 2+) tarafindan "
                    "UNSCHEDULABLE olarak isaretlenir ve uretimde atlanir. "
                    "Admin uyarisi Control Center'da gosterilir."
                ) if total > 0 else
                self.style.SUCCESS(
                    "\nTum medya kayitlari 15sn planning grid ile uyumludur."
                )
            )
