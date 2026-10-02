from urllib.parse import quote, unquote, urlsplit

from django.conf import settings
from django.db import migrations


def _extract_key(url):
    if "x-amz-" not in (url or "").lower():
        return ""
    path = unquote(urlsplit(url).path).lstrip("/")
    bucket = getattr(settings, "S3_BUCKET", "").strip("/")
    if bucket and path.startswith(f"{bucket}/"):
        path = path[len(bucket) + 1:]
    if not path or ".." in path or "//" in path:
        return ""
    return path


def forwards(apps, schema_editor):
    BarkodLogo = apps.get_model("barkod_logo", "BarkodLogo")
    base = getattr(settings, "API_BASE_URL", "").rstrip("/")
    for logo in BarkodLogo.objects.all().iterator():
        if "x-amz-" not in (logo.media_url or "").lower():
            continue
        key = logo.object_key or _extract_key(logo.media_url)
        if not key:
            continue
        logo.object_key = key
        logo.media_url = f"{base}/api/media/{quote(key, safe='/')}"
        logo.save(update_fields=["object_key", "media_url"])


class Migration(migrations.Migration):
    dependencies = [("barkod_logo", "0002_alter_barkodlogo_aktif_and_more")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
