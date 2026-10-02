"""RustFS nesnelerini object_key uzerinden guvenli olarak stream etme yardimcilari."""

from __future__ import annotations

import mimetypes
import re
from urllib.parse import quote

from django.conf import settings
from django.http import StreamingHttpResponse
from django.urls import reverse

from apps.core.services.storage_service import StorageService


_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


def validate_media_object_key(object_key: str) -> str:
    """Proxy tarafinda kabul edilen canonical RustFS anahtarini dondurur."""
    key = (object_key or "").strip()
    if not key or key.startswith(("/", "\\")) or ".." in key or "\\" in key or "//" in key:
        raise ValueError("Gecersiz medya anahtari.")
    if not key.startswith(("ads/", "barkod-logo/")):
        raise ValueError("Bu nesne medya proxy'sinden sunulamaz.")
    return key


def media_proxy_path(object_key: str) -> str:
    key = validate_media_object_key(object_key)
    return reverse("media-proxy", kwargs={"object_key": key})


def media_proxy_url(object_key: str, request=None) -> str:
    """Request varsa mutlak, yoksa API_BASE_URL tabanli kalici proxy URL'i."""
    path = media_proxy_path(object_key)
    if request is not None:
        return request.build_absolute_uri(path)
    base = getattr(settings, "API_BASE_URL", "").rstrip("/")
    return f"{base}{path}" if base else path


def stream_storage_object(request, object_key: str):
    """RustFS nesnesini HTTP Range destekli olarak stream eder."""
    key = validate_media_object_key(object_key)
    storage = StorageService()
    stat = storage.client.stat_object(storage.bucket_name, key)
    total = stat.size
    start, end = 0, max(total - 1, 0)
    status_code = 200

    raw_range = request.META.get("HTTP_RANGE", "")
    if raw_range:
        match = _RANGE_RE.fullmatch(raw_range.strip())
        if not match or "," in raw_range:
            raise ValueError("Gecersiz Range basligi.")
        first, last = match.groups()
        if not first and not last:
            raise ValueError("Gecersiz Range basligi.")
        if first:
            start = int(first)
            end = int(last) if last else total - 1
        else:
            suffix = int(last)
            if suffix <= 0:
                raise ValueError("Gecersiz Range basligi.")
            start = max(total - suffix, 0)
            end = total - 1
        if start >= total or end < start:
            raise ValueError("Range nesne boyutunun disinda.")
        end = min(end, total - 1)
        status_code = 206

    length = max(end - start + 1, 0)
    response = storage.client.get_object(storage.bucket_name, key, offset=start, length=length)

    def chunks():
        try:
            for chunk in response.stream(amt=65536):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    content_type = mimetypes.guess_type(key)[0] or getattr(stat, "content_type", None) or "application/octet-stream"
    http_response = StreamingHttpResponse(chunks(), status=status_code, content_type=content_type)
    http_response["Accept-Ranges"] = "bytes"
    http_response["Content-Length"] = str(length)
    http_response["Cache-Control"] = "private, max-age=86400"
    http_response["Content-Disposition"] = f'inline; filename="{quote(key.rsplit("/", 1)[-1])}"'
    if status_code == 206:
        http_response["Content-Range"] = f"bytes {start}-{end}/{total}"
    return http_response
