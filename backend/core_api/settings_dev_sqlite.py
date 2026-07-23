"""Local development settings - SQLite (browser testing)."""
import os
os.environ.setdefault("S3_PUBLIC_BASE_URL", "http://localhost:9000/dev")
from core_api.settings import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db_dev.sqlite3",
    }
}
DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

# Throttle: sınıfları kaldır ama rates'i koru (ScopedRateThrottle güvenli)
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
# NOT: DEFAULT_THROTTLE_RATES kasıtla korunuyor (ScopedRateThrottle.get_rate için)

# Cache backend — throttle + session için
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Dev server için tüm logları dosyaya da yaz (500 traceback için)
import pathlib as _pl
_LOG_DIR = _pl.Path(BASE_DIR) / "logs"
_LOG_DIR.mkdir(exist_ok=True)
LOGGING["handlers"]["dev_file"] = {
    "class": "logging.FileHandler",
    "filename": str(_LOG_DIR / "dev_server.log"),
    "formatter": "readable",
    "level": "DEBUG",
}
LOGGING["root"]["handlers"].append("dev_file")
LOGGING["loggers"]["eisa.errors"]["handlers"] = ["console_readable", "dev_file"]
