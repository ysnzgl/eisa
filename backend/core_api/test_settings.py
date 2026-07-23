"""Test ayarları — SQLite ile, harici servis gerektirmez."""
import os

# S3_PUBLIC_BASE_URL: bucket dahil (format: <endpoint>/<bucket>)
# Test ortamında S3_ENDPOINT=localhost:9000, S3_BUCKET=dev varsayılanları kullanılır.
os.environ.setdefault("S3_PUBLIC_BASE_URL", "http://localhost:9000/dev")

from core_api.settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Test sırasında parola hashlemeyi hızlandır
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Throttle devre dışı — test sonuçlarını etkilemesin
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []

# Sentry devre dışı
SENTRY_DSN = ""
