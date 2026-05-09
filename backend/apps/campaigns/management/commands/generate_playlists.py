"""``python manage.py generate_playlists [--date YYYY-MM-DD] [--kiosk <id>]``

Cron / scheduler dostu giris noktasi. Tek bir kiosk veya tum aktif kiosklar
icin ``Playlist`` ve ``PlaylistItem`` kayitlarini (yeniden) uretir.
"""
from __future__ import annotations

import datetime as _dt

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.campaigns.services.scheduler import generate_for_kiosk
from apps.pharmacies.models import Kiosk


class Command(BaseCommand):
    help = "DOOH Playlist'lerini (yeniden) uretir."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--date", default=None,
                            help="YYYY-MM-DD; varsayilan: yarin (UTC).")
        parser.add_argument("--kiosk", type=int, default=None,
                            help="Tek kiosk id'si; verilmezse tum aktif kiosklar.")

    def handle(self, *args, **options):
        target_date = self._parse_date(options.get("date"))
        kiosk_id = options.get("kiosk")

        qs = Kiosk.objects.filter(aktif=True)
        if kiosk_id is not None:
            qs = qs.filter(pk=kiosk_id)

        total = 0
        for kiosk in qs:
            playlists = generate_for_kiosk(kiosk, target_date)
            total += len(playlists)
            self.stdout.write(
                f"  ✓ kiosk={kiosk.pk} {target_date} -> {len(playlists)} playlist"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Toplam {total} playlist uretildi (date={target_date})."
        ))

    @staticmethod
    def _parse_date(raw: str | None) -> _dt.date:
        if raw is None:
            return (timezone.now() + _dt.timedelta(days=1)).date()
        try:
            return _dt.datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError(f"Gecersiz tarih: {raw}") from exc
