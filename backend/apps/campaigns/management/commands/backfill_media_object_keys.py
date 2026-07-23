"""Backfill management command - Faz 0.5.

Eski presigned/eksik media_url kayitlarindan object_key tureten
forward-only backfill komutu.

GUVENLIK KURALLARI:
  - Yalniz izin verilen S3 endpoint/bucket host larini kabul eder.
  - Bucket/path-style eslesme zorunludur; yabanci host reddedilir.
  - URL decode + path traversal korumasi (//, ..) uygulanir.
  - Query string korlemesine kesilmez; presigned parametreler dogrulanir.
  - --apply modunda HEAD dogrulamasi varsayilan ve zorunludur.
  - HEAD dogrulamasi yalniz --skip-head-check-DANGEROUS ile atlanabilir.
  - Dogrulanamayan kayit kesinlikle degistirilmez.

Kullanim:
    python manage.py backfill_media_object_keys            # dry-run
    python manage.py backfill_media_object_keys --apply    # HEAD dogrulama ile yaz
    python manage.py backfill_media_object_keys --apply --skip-head-check-DANGEROUS
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.campaigns.models import Creative, HouseAd


_PRESIGNED_MARKERS = ("X-Amz-", "x-amz-", "AWSAccessKeyId=", "awsaccesskeyid=")


@dataclass
class BackfillResult:
    already_filled: int = 0
    updated: int = 0
    failed: int = 0
    failures: list = field(default_factory=list)


def _is_presigned(url: str) -> bool:
    return any(m in url for m in _PRESIGNED_MARKERS)


def _allowed_hosts(endpoint: str) -> frozenset:
    """Izin verilen host:port ciflerinin kumesi.

    S3_ENDPOINT (host:port) ve S3_PUBLIC_BASE_URL'nin netloc'u eklenir.
    S3_PUBLIC_BASE_URL bucket adini icerdigi icin path'i degil yalniz netloc'u aliriz.
    """
    hosts = set()
    if endpoint:
        hosts.add(endpoint.split("://")[-1].rstrip("/").lower())
    public_base = getattr(settings, "S3_PUBLIC_BASE_URL", "")
    if public_base:
        parsed = urllib.parse.urlparse(public_base)
        hosts.add(parsed.netloc.lower())
    return frozenset(hosts)


def _extract_object_key(
    media_url: str,
    endpoint: str,
    bucket: str,
    public_base: str,
    allowed_hosts: frozenset,
) -> tuple:
    """media_url den object_key turet.
    Doner: (object_key | None, durum_aciklamasi)
    """
    if not media_url:
        return None, "empty_url"

    try:
        decoded = urllib.parse.unquote(media_url)
    except Exception:
        return None, "url_decode_error"

    path = urllib.parse.urlparse(decoded).path
    netloc = urllib.parse.urlparse(decoded).netloc

    if "//" in path or ".." in path:
        return None, "path_traversal_detected"

    host = netloc.lower()
    if allowed_hosts and host not in allowed_hosts:
        return None, f"host_not_allowed: {host!r} allowed={sorted(allowed_hosts)!r}"

    # Durum 1: Zaten stabil URL (S3_PUBLIC_BASE_URL ile basliyor)
    # Sozlesme: S3_PUBLIC_BASE_URL bucket adini icerir
    # → https://files.eisa.com.tr/eisa-files/ads/abc.mp4 → key=ads/abc.mp4
    if public_base:
        clean_base = public_base.rstrip("/")
        stable_prefix = f"{clean_base}/"
        if decoded.startswith(stable_prefix) and not _is_presigned(decoded):
            key = decoded[len(stable_prefix):].split("?")[0]
            if key and "//" not in key and ".." not in key:
                return key, "already_stable"
                key = decoded[len(prefix):].split("?")[0]
                if key and "//" not in key and ".." not in key:
                    return key, "already_stable"

    # Durum 2: Path-style S3 URL (presigned veya direct)
    expected_prefix = f"/{bucket}/"
    if not path.startswith(expected_prefix):
        return None, f"no_bucket_prefix: path={path!r} expected={expected_prefix!r}"

    key = path[len(expected_prefix):]
    if not key:
        return None, "empty_key_after_bucket"

    if ".." in key or "//" in key:
        return None, f"path_traversal_in_key: {key!r}"

    reason = "already_stable" if not _is_presigned(decoded) else "ok"
    return key, reason


def _head_check(storage_service, object_key: str) -> tuple:
    try:
        storage_service.client.stat_object(storage_service.bucket_name, object_key)
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _backfill_queryset(
    qs, model_label, endpoint, bucket, public_base, allowed_hosts,
    apply, skip_head_check, storage_service, result, stdout,
):
    for obj in qs:
        if obj.object_key:
            result.already_filled += 1
            continue

        key, reason = _extract_object_key(
            obj.media_url, endpoint, bucket, public_base, allowed_hosts
        )

        if key is None:
            result.failed += 1
            result.failures.append({
                "model": model_label, "id": str(obj.pk),
                "media_url": obj.media_url, "reason": reason,
            })
            stdout.write(f"  [FAIL] {model_label} pk={obj.pk}: {reason}")
            continue

        if apply and not skip_head_check:
            ok, err = _head_check(storage_service, key)
            if not ok:
                result.failed += 1
                result.failures.append({
                    "model": model_label, "id": str(obj.pk),
                    "media_url": obj.media_url, "reason": f"head_check_failed: {err}",
                })
                stdout.write(f"  [HEAD FAIL] {model_label} pk={obj.pk}: key={key!r} err={err}")
                continue

        if public_base:
            base = public_base.rstrip("/")
        else:
            s3_secure = getattr(settings, "S3_SECURE", False)
            scheme = "https" if s3_secure else "http"
            base = f"{scheme}://{endpoint}"
        new_media_url = f"{base}/{bucket}/{key}"

        if apply:
            obj.object_key = key
            obj.media_url = new_media_url
            obj.save(update_fields=["object_key", "media_url"])
            stdout.write(f"  [OK] {model_label} pk={obj.pk}: key={key!r}")
        else:
            stdout.write(
                f"  [DRY-RUN] {model_label} pk={obj.pk}: "
                f"key={key!r} new_url={new_media_url!r} reason={reason!r}"
            )

        result.updated += 1


class Command(BaseCommand):
    help = (
        "Faz 0.5 backfill: presigned/eksik object_key kayitlari icin "
        "object_key + kalici URL doldurur. Varsayilan dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true", default=False,
            help="DB ye yaz (HEAD dogrulama ile).",
        )
        parser.add_argument(
            "--skip-head-check-DANGEROUS",
            dest="skip_head_check",
            action="store_true",
            default=False,
            help="TEHLIKELI: HEAD dogrulamasini atla. Normal rollout ta kullanilmaz.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        skip_head_check = options["skip_head_check"]

        if skip_head_check and apply:
            self.stdout.write(self.style.ERROR(
                "\n UYARI: --skip-head-check-DANGEROUS aktif.\n"
            ))

        endpoint = getattr(settings, "S3_ENDPOINT",
                           getattr(settings, "RUSTFS_ENDPOINT", ""))
        bucket = getattr(settings, "S3_BUCKET",
                         getattr(settings, "RUSTFS_BUCKET_NAME", ""))
        public_base = getattr(settings, "S3_PUBLIC_BASE_URL", "").rstrip("/")

        if not bucket:
            self.stderr.write(self.style.ERROR("S3_BUCKET ayari bulunamadi."))
            return

        allowed = _allowed_hosts(endpoint)
        mode = (
            "APPLY (HEAD dogrulamali)" if apply and not skip_head_check
            else "APPLY (HEAD ATLANILA - DANGEROUS)" if apply
            else "DRY-RUN"
        )

        self.stdout.write(self.style.WARNING(
            f"\n=== backfill_media_object_keys [{mode}] ===\n"
            f"  endpoint      : {endpoint}\n"
            f"  bucket        : {bucket}\n"
            f"  public_base   : {public_base or '(bos)'}\n"
            f"  allowed_hosts : {sorted(allowed)}\n"
        ))

        storage_service = None
        if apply and not skip_head_check:
            from apps.core.services.storage_service import StorageService
            storage_service = StorageService()

        result = BackfillResult()

        self.stdout.write("\n--- Creative ---")
        _backfill_queryset(
            qs=Creative.objects.filter(object_key__isnull=True),
            model_label="Creative", endpoint=endpoint, bucket=bucket,
            public_base=public_base, allowed_hosts=allowed,
            apply=apply, skip_head_check=skip_head_check,
            storage_service=storage_service, result=result, stdout=self.stdout,
        )

        self.stdout.write("\n--- HouseAd ---")
        _backfill_queryset(
            qs=HouseAd.objects.filter(object_key__isnull=True),
            model_label="HouseAd", endpoint=endpoint, bucket=bucket,
            public_base=public_base, allowed_hosts=allowed,
            apply=apply, skip_head_check=skip_head_check,
            storage_service=storage_service, result=result, stdout=self.stdout,
        )

        self.stdout.write(self.style.SUCCESS(
            f"\n=== Rapor [{mode}] ===\n"
            f"  Zaten dolu              : {result.already_filled}\n"
            f"  Islendi / guncellenecek : {result.updated}\n"
            f"  Basarisiz               : {result.failed}\n"
        ))

        if result.failures:
            self.stdout.write(self.style.ERROR("\n--- Basarisiz Kayitlar ---"))
            for f in result.failures:
                self.stdout.write(
                    f"  [{f['model']}] id={f['id']} reason={f['reason']}\n"
                    f"    url={f['media_url']}"
                )

        if not apply:
            self.stdout.write(self.style.WARNING(
                "\nDry-run tamamlandi. Degisiklikleri uygulamak icin: --apply"
            ))
