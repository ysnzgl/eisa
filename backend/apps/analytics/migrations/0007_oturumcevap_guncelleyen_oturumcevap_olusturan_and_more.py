# 2026-07-20 — Production-safe QR data cleanup.
#
# Problem: qr_kodu had no unique constraint. Over time some rows may have:
#   - Empty values ('')
#   - Invalid format (not exactly 8 uppercase A-Z0-9 chars)
#   - Duplicate values (same code on two different sessions)
#
# Strategy:
#   1. Find all invalid (empty or wrong-format) qr_kodu values → assign new unique code.
#   2. Find duplicates among remaining rows → keep the oldest (lowest id), reassign the rest.
#   3. Process in batches of 500 to avoid loading the whole table into memory.
#   4. Idempotent: safe to run twice (already-valid unique values are untouched).
#
# After this migration 0008 can safely add unique=True + max_length=8.

import re
import secrets
import string

from django.db import migrations

QR_ALPHABET = string.ascii_uppercase + string.digits  # A-Z 0-9
QR_LENGTH = 8
QR_RE = re.compile(r'^[A-Z0-9]{8}$')
BATCH_SIZE = 500


def _generate_candidate(existing: set) -> str:
    """Generate a random 8-char code not in the given set."""
    for _ in range(50):
        code = ''.join(secrets.choice(QR_ALPHABET) for _ in range(QR_LENGTH))
        if code not in existing:
            return code
    raise RuntimeError("QR generation failed after 50 attempts — alphabet space exhausted?")


def clean_qr_codes(apps, schema_editor):
    OturumLogu = apps.get_model('analytics', 'OturumLogu')

    # Collect ALL currently valid, non-duplicate QR codes to avoid collisions when
    # generating replacements. We load only the qr_kodu column (small).
    known_valid = set(
        OturumLogu.objects.exclude(qr_kodu='')
        .filter(qr_kodu__regex=r'^[A-Z0-9]{8}$')
        .values_list('qr_kodu', flat=True)
    )

    # ── Step 1: Fix empty or invalid-format QR codes ─────────────────────────
    invalid_ids = list(
        OturumLogu.objects
        .exclude(qr_kodu__regex=r'^[A-Z0-9]{8}$')
        .values_list('id', flat=True)
        .iterator(chunk_size=BATCH_SIZE)
    )
    fixed_invalid = 0
    for pk in invalid_ids:
        new_code = _generate_candidate(known_valid)
        known_valid.add(new_code)
        OturumLogu.objects.filter(pk=pk).update(qr_kodu=new_code)
        fixed_invalid += 1

    # ── Step 2: Fix duplicates (keep oldest record, reassign the rest) ────────
    # Count occurrences; collect duplicates in batches via distinct qr_kodu values.
    from django.db.models import Count
    dup_qrs = (
        OturumLogu.objects
        .values('qr_kodu')
        .annotate(cnt=Count('id'))
        .filter(cnt__gt=1)
        .values_list('qr_kodu', flat=True)
    )

    fixed_duplicates = 0
    for dup_qr in dup_qrs.iterator(chunk_size=BATCH_SIZE):
        # Keep the record with the smallest id (oldest); reassign the rest
        ids = list(
            OturumLogu.objects
            .filter(qr_kodu=dup_qr)
            .order_by('id')
            .values_list('id', flat=True)
        )
        for pk in ids[1:]:   # Skip the first (keep it)
            new_code = _generate_candidate(known_valid)
            known_valid.add(new_code)
            OturumLogu.objects.filter(pk=pk).update(qr_kodu=new_code)
            fixed_duplicates += 1

    if fixed_invalid or fixed_duplicates:
        print(
            f'\n  [qr_cleanup] Fixed {fixed_invalid} invalid + '
            f'{fixed_duplicates} duplicate QR codes.'
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    """Data migration: clean invalid/duplicate QR codes before adding unique constraint."""

    dependencies = [
        ('analytics', '0006_session_normalization'),
    ]

    operations = [
        migrations.RunPython(clean_qr_codes, reverse_code=noop),
    ]
