"""Read-only data quality report for session normalization state.

Usage:
    python manage.py verify_session_data

Reports (does NOT modify any data):
  - Total sessions
  - Empty QR count
  - Invalid-format QR count  (not [A-Z0-9]{8})
  - Duplicate QR groups
  - Sessions with OturumCevap records (normalized)
  - Sessions with raw cevaplar JSON but no OturumCevap (backfill candidates)
  - Sessions with OturumOnerilenEtkenMadde records (normalized)
  - Sessions with raw onerilen_etken_maddeler JSON but no child records
  - Unconvertible JSON cevap values (non-integer keys/values)
"""
from __future__ import annotations

import re

from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from apps.analytics.models import OturumCevap, OturumLogu, OturumOnerilenEtkenMadde

QR_RE = re.compile(r'^[A-Z0-9]{8}$')
BATCH = 1000


class Command(BaseCommand):
    help = "Read-only data quality report — does not modify any data."

    def handle(self, *args, **options):
        total = OturumLogu.objects.count()
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"  SESSION DATA QUALITY REPORT")
        self.stdout.write(f"{'='*60}\n")
        self.stdout.write(f"Total sessions          : {total}")

        # QR quality
        empty_qr = OturumLogu.objects.filter(Q(qr_kodu='') | Q(qr_kodu__isnull=True)).count()
        self.stdout.write(f"Empty QR                : {empty_qr}")

        invalid_qr = OturumLogu.objects.exclude(qr_kodu='').exclude(
            qr_kodu__regex=r'^[A-Z0-9]{8}$'
        ).count()
        self.stdout.write(f"Invalid-format QR       : {invalid_qr}")

        dup_groups = (
            OturumLogu.objects
            .values('qr_kodu')
            .annotate(cnt=Count('id'))
            .filter(cnt__gt=1)
        )
        dup_count = dup_groups.count()
        dup_rows = sum(g['cnt'] - 1 for g in dup_groups)
        self.stdout.write(f"Duplicate QR groups     : {dup_count} ({dup_rows} rows need reassignment)")

        # Normalization state
        sessions_with_cevap = OturumCevap.objects.values('oturum_id').distinct().count()
        sessions_with_onerilen = OturumOnerilenEtkenMadde.objects.values('oturum_id').distinct().count()
        self.stdout.write(f"\nSessions with OturumCevap       : {sessions_with_cevap}")
        self.stdout.write(f"Sessions with OturumOnerilen    : {sessions_with_onerilen}")

        # Backfill candidates (have JSON data but no child records yet)
        cevap_normalized_ids = set(
            OturumCevap.objects.values_list('oturum_id', flat=True).distinct()
        )
        backfill_cevap = 0
        unconvertible = 0
        for oturum in OturumLogu.objects.exclude(cevaplar={}).iterator(chunk_size=BATCH):
            if oturum.pk in cevap_normalized_ids:
                continue
            raw = oturum.cevaplar
            if isinstance(raw, dict) and raw:
                backfill_cevap += 1
                for k, v in raw.items():
                    try:
                        int(k)
                    except (ValueError, TypeError):
                        unconvertible += 1
                        break

        onerilen_normalized_ids = set(
            OturumOnerilenEtkenMadde.objects.values_list('oturum_id', flat=True).distinct()
        )
        backfill_onerilen = 0
        for oturum in OturumLogu.objects.exclude(onerilen_etken_maddeler=[]).iterator(chunk_size=BATCH):
            if oturum.pk in onerilen_normalized_ids:
                continue
            raw = oturum.onerilen_etken_maddeler
            if isinstance(raw, list) and raw:
                backfill_onerilen += 1

        self.stdout.write(f"\nBackfill candidates:")
        self.stdout.write(f"  cevaplar JSON→OturumCevap   : {backfill_cevap}")
        self.stdout.write(f"  onerilen JSON→OturumOnerilen: {backfill_onerilen}")
        self.stdout.write(f"  Unconvertible cevap keys    : {unconvertible}")

        self.stdout.write(f"\n{'='*60}")
        if empty_qr or invalid_qr or dup_count or backfill_cevap or backfill_onerilen:
            self.stdout.write(
                self.style.WARNING(
                    "  ACTION NEEDED: Run migrations 0007+0008 for QR cleanup.\n"
                    "  Run: python manage.py backfill_session_normalization\n"
                    "  for JSON→relational backfill."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("  All data is clean and normalized."))
        self.stdout.write(f"{'='*60}\n")
