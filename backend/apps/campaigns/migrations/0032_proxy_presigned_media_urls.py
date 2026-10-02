from urllib.parse import quote, unquote, urlsplit

from django.conf import settings
from django.db import migrations


def _is_presigned(url):
    return "x-amz-" in (url or "").lower()


def _extract_key(url):
    if not _is_presigned(url):
        return ""
    path = unquote(urlsplit(url).path).lstrip("/")
    bucket = getattr(settings, "S3_BUCKET", "").strip("/")
    if bucket and path.startswith(f"{bucket}/"):
        path = path[len(bucket) + 1:]
    if not path or ".." in path or "//" in path:
        return ""
    return path


def _proxy_url(key):
    base = getattr(settings, "API_BASE_URL", "").rstrip("/")
    return f"{base}/api/media/{quote(key, safe='/')}"


def forwards(apps, schema_editor):
    Creative = apps.get_model("campaigns", "Creative")
    for creative in Creative.objects.all().iterator():
        changed = []
        if _is_presigned(creative.media_url):
            key = creative.object_key or _extract_key(creative.media_url)
            if key:
                creative.object_key = key
                creative.media_url = _proxy_url(key)
                changed.extend(["object_key", "media_url"])
        if _is_presigned(creative.active_media_url):
            key = creative.active_object_key or _extract_key(creative.active_media_url)
            if key:
                creative.active_object_key = key
                creative.active_media_url = _proxy_url(key)
                changed.extend(["active_object_key", "active_media_url"])
        if changed:
            creative.save(update_fields=list(dict.fromkeys(changed)))


class Migration(migrations.Migration):
    dependencies = [("campaigns", "0031_alter_idlescreencontent_baslik_en")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
