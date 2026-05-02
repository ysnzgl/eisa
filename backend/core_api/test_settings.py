"""Test ayarları — SQLite ile, harici servis gerektirmez."""
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
