"""Idempotent backfill: migrate old JSON session data to relational child tables.

Usage:
    python manage.py backfill_session_normalization [--batch-size N] [--dry-run]

What it does:
  1. Finds OturumLogu records that have non-empty cevaplar JSON
     but no OturumCevap children yet.
  2. Finds OturumLogu records that have non-empty onerilen_etken_maddeler JSON
     but no OturumOnerilenEtkenMadde children yet.
  3. Creates the missing child records (uses get_or_create — safe to re-run).
  4. Reports unresolvable values (non-integer keys, unknown FK IDs) rather than
     silently dropping them.

Deployment order:
  1. Apply migrations (0006, 0007, 0008).
  2. Run this command once post-deploy (or as part of post-deploy hook).
  3. Re-running is safe (idempotent).

This is intentionally a management command rather than a migration because
backfilling large tables can take significant time and should not block
database migrations during deploy.
"""
from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.analytics.models import OturumCevap, OturumLogu, OturumOnerilenEtkenMadde
from apps.products.models import Cevap, EtkenMadde, Soru

logger = logging.getLogger(__name__)

DEFAULT_BATCH = 200


class Command(BaseCommand):
    help = "Backfill JSON session data into OturumCevap / OturumOnerilenEtkenMadde."

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size', type=int, default=DEFAULT_BATCH,
            help=f'Sessions per batch (default {DEFAULT_BATCH}).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be created without writing anything.',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no data will be written."))

        # Pre-fetch normalized session IDs to skip them quickly
        normalized_cevap_ids = set(
            OturumCevap.objects.values_list('oturum_id', flat=True).distinct()
        )
        normalized_onerilen_ids = set(
            OturumOnerilenEtkenMadde.objects.values_list('oturum_id', flat=True).distinct()
        )

        total_cevap_created = 0
        total_onerilen_created = 0
        total_skipped = 0
        unresolvable: list[dict] = []

        qs = OturumLogu.objects.iterator(chunk_size=batch_size)

        for oturum in qs:
            needs_cevap = (
                oturum.pk not in normalized_cevap_ids
                and isinstance(oturum.cevaplar, dict)
                and oturum.cevaplar
            )
            needs_onerilen = (
                oturum.pk not in normalized_onerilen_ids
                and isinstance(oturum.onerilen_etken_maddeler, list)
                and oturum.onerilen_etken_maddeler
            )

            if not needs_cevap and not needs_onerilen:
                continue

            try:
                with transaction.atomic():
                    if needs_cevap:
                        created = _backfill_cevaplar(oturum, dry_run, unresolvable)
                        total_cevap_created += created
                        normalized_cevap_ids.add(oturum.pk)

                    if needs_onerilen:
                        created = _backfill_onerilen(oturum, dry_run, unresolvable)
                        total_onerilen_created += created
                        normalized_onerilen_ids.add(oturum.pk)

            except Exception as exc:
                total_skipped += 1
                unresolvable.append({
                    "oturum_id": oturum.pk,
                    "reason": f"Transaction error: {exc}",
                })

        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"  BACKFILL COMPLETE{' (DRY RUN)' if dry_run else ''}")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"OturumCevap records created       : {total_cevap_created}")
        self.stdout.write(f"OturumOnerilenEtkenMadde created  : {total_onerilen_created}")
        self.stdout.write(f"Sessions skipped (errors)         : {total_skipped}")
        if unresolvable:
            self.stdout.write(self.style.WARNING(f"Unresolvable / skipped ({len(unresolvable)}):"))
            for item in unresolvable[:20]:
                self.stdout.write(f"  oturum_id={item['oturum_id']}: {item['reason']}")
            if len(unresolvable) > 20:
                self.stdout.write(f"  ... and {len(unresolvable) - 20} more")
        self.stdout.write(f"{'='*60}\n")


def _parse_int(value) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _backfill_cevaplar(oturum: OturumLogu, dry_run: bool, unresolvable: list) -> int:
    """Returns count of OturumCevap records created."""
    created = 0
    for soru_id_str, cevap_value in oturum.cevaplar.items():
        soru_id = _parse_int(soru_id_str)
        if soru_id is None:
            unresolvable.append({
                "oturum_id": oturum.pk,
                "reason": f"Non-integer soru key: {soru_id_str!r}",
            })
            continue

        soru = Soru.objects.filter(id=soru_id).first()
        cevap = None
        cevap_metin = ""

        cevap_id = _parse_int(cevap_value)
        if cevap_id is not None:
            cevap_obj = Cevap.objects.filter(id=cevap_id).first()
            if cevap_obj:
                if soru and cevap_obj.soru_id != soru_id:
                    unresolvable.append({
                        "oturum_id": oturum.pk,
                        "reason": (
                            f"Cevap {cevap_id} belongs to soru {cevap_obj.soru_id}"
                            f" not {soru_id} — stored with null cevap FK"
                        ),
                    })
                else:
                    cevap = cevap_obj
                    cevap_metin = cevap_obj.metin
            else:
                unresolvable.append({
                    "oturum_id": oturum.pk,
                    "reason": f"Cevap id={cevap_id} not found — snapshot only",
                })
        else:
            cevap_metin = str(cevap_value)

        if not dry_run:
            OturumCevap.objects.get_or_create(
                oturum=oturum,
                soru=soru,
                defaults={
                    "cevap": cevap,
                    "soru_metni_snapshot": soru.metin if soru else f"Soru #{soru_id}",
                    "cevap_metni_snapshot": cevap_metin,
                    "cevap_degeri_snapshot": str(cevap_value),
                },
            )
        created += 1
    return created


def _backfill_onerilen(oturum: OturumLogu, dry_run: bool, unresolvable: list) -> int:
    """Returns count of OturumOnerilenEtkenMadde records created."""
    created = 0
    for value in oturum.onerilen_etken_maddeler:
        etken_madde = None
        etken_madde_adi = ""

        if isinstance(value, dict):
            em_id = _parse_int(value.get("id"))
            if em_id:
                em = EtkenMadde.objects.filter(id=em_id).first()
                if em:
                    etken_madde = em
                    etken_madde_adi = em.ad
                else:
                    unresolvable.append({
                        "oturum_id": oturum.pk,
                        "reason": f"EtkenMadde id={em_id} not found — snapshot only",
                    })
            etken_madde_adi = etken_madde_adi or value.get("ad", str(value))
        elif isinstance(value, (int, str)):
            em_id = _parse_int(value)
            if em_id is not None:
                em = EtkenMadde.objects.filter(id=em_id).first()
                if em:
                    etken_madde = em
                    etken_madde_adi = em.ad
                else:
                    unresolvable.append({
                        "oturum_id": oturum.pk,
                        "reason": f"EtkenMadde id={em_id} not found — snapshot only",
                    })
                    etken_madde_adi = f"Etken Madde #{em_id}"
            else:
                etken_madde_adi = str(value)

        if not (etken_madde or etken_madde_adi):
            continue

        if not dry_run:
            OturumOnerilenEtkenMadde.objects.get_or_create(
                oturum=oturum,
                etken_madde=etken_madde,
                defaults={"etken_madde_adi_snapshot": etken_madde_adi},
            )
        created += 1
    return created
