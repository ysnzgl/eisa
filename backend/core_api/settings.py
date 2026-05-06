"""
Django ayarları — E-İSA Merkezi API.

KVKK uyumu: tüm kişisel olmayan demografik veriler anonim toplanır.
"""
import json
import logging
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)

SECRET_KEY = config("DJANGO_SECRET_KEY", default="dev-only-change-me" if DEBUG else "")
if not DEBUG and (not SECRET_KEY or SECRET_KEY == "dev-only-change-me"):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY üretimde mutlaka güçlü ve rastgele bir değere ayarlanmalıdır."
    )
# SEC-006: zayıf/kısa secret'ları üretimde bloka.
if not DEBUG and len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY en az 50 karakter olmalıdır (entropi gereksinimi)."
    )

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1" if DEBUG else "",
    cast=Csv(),
)
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS üretimde açık bir host listesi içermelidir; '*' kabul edilmez."
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Üçüncü parti
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    # Yerel uygulamalar
    "apps.core",
    "apps.lookups",
    "apps.users",
    "apps.pharmacies",
    "apps.products",
    "apps.analytics",
    "apps.campaigns",
    "apps.audit",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core_api.urls"
WSGI_APPLICATION = "core_api.wsgi.application"
ASGI_APPLICATION = "core_api.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB", default="eisa"),
        "USER": config("POSTGRES_USER", default="eisa"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="eisa" if DEBUG else ""),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}
if not DEBUG and (not DATABASES["default"]["PASSWORD"] or DATABASES["default"]["PASSWORD"] == "eisa"):
    raise ImproperlyConfigured(
        "POSTGRES_PASSWORD üretimde güçlü ve rastgele bir değere ayarlanmalıdır."
    )

# Django'nun yerleşik parola güvenlik politikaları
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "users.Kullanici"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Paneller: httpOnly çerez tabanlı JWT (SEC-002).
        # Authorization başlığı geriye dönük uyumluluk için hâlâ desteklenir.
        "core_api.cookie_jwt.JWTCookieAuthentication",
        # Kiosk: App-Key (apps.pharmacies.auth)
        "apps.pharmacies.auth.KioskAppKeyAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core_api.exception_handler.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("THROTTLE_ANON", default="100/hour"),
        "user": config("THROTTLE_USER", default="2000/hour"),
        "login": config("THROTTLE_LOGIN", default="5/min"),
        # SEC-008: Hassas admin işlemleri (örn. kiosk app_key yenileme).
        "admin_sensitive": config("THROTTLE_ADMIN_SENSITIVE", default="10/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_TTL_MIN", default=30, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_TTL_DAYS", default=7, cast=int)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

# ─── JWT httpOnly Çerez Ayarları (SEC-002) ──────────────────────────────────
JWT_AUTH_COOKIE = config("JWT_AUTH_COOKIE", default="eisa_access")
JWT_REFRESH_COOKIE = config("JWT_REFRESH_COOKIE", default="eisa_refresh")
JWT_COOKIE_SAMESITE = config("JWT_COOKIE_SAMESITE", default="Strict")
JWT_COOKIE_SECURE = config("JWT_COOKIE_SECURE", default=not DEBUG, cast=bool)
JWT_COOKIE_DOMAIN = config("JWT_COOKIE_DOMAIN", default=None)
if JWT_COOKIE_DOMAIN == "":
    JWT_COOKIE_DOMAIN = None

CORS_ALLOWED_ORIGINS = config(
    "DJANGO_CORS_ORIGINS",
    default="",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)
# Development ortamında tüm originleri kabul et, üretimde whitelist kullan
CORS_ALLOW_ALL_ORIGINS = DEBUG
# httpOnly JWT çerezlerinin cross-origin panel istekleriyle gönderilebilmesi için.
CORS_ALLOW_CREDENTIALS = True
if not DEBUG and not CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "DJANGO_CORS_ORIGINS üretimde panel domain(leri) ile doldurulmalıdır."
    )
# SEC-007: CORS allow-list yalnızca https:// ile başlayan tam origin'leri kabul etsin.
if not DEBUG:
    for _origin in CORS_ALLOWED_ORIGINS:
        if not _origin.startswith("https://"):
            raise ImproperlyConfigured(
                f"DJANGO_CORS_ORIGINS üretimde sadece HTTPS origin'leri kabul eder: {_origin}"
            )
        if "*" in _origin:
            raise ImproperlyConfigured(
                "DJANGO_CORS_ORIGINS wildcard ('*') içermemelidir."
            )

# Üretim güvenlik başlıkları (Traefik HTTPS sonlandırması arkasında)
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"
    SECURE_HSTS_SECONDS = 31536000  # 1 yıl
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"

LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Istanbul"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── API Dokümantasyonu (yalnızca geliştirme ortamında) ─────────────────────
if DEBUG:
    SPECTACULAR_SETTINGS = {
        "TITLE": "E-İSA Merkezi API",
        "DESCRIPTION": (
            "E-İSA panel API'si — yönetici ve eczacı panelleri için JWT korumalı endpoint'ler. "
            "Kiosk kimlik doğrulaması App-Key başlığı (X-App-Key + X-Kiosk-Mac) ile yapılır."
        ),
        "VERSION": "1.0.0",
        "SERVE_INCLUDE_SCHEMA": False,
        "COMPONENT_SPLIT_REQUEST": True,
        "SECURITY": [{"jwtAuth": []}],
        "APPEND_COMPONENTS": {
            "securitySchemes": {
                "jwtAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                },
                "kioskAppKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-App-Key",
                },
            }
        },
        "TAGS": [
            {"name": "auth", "description": "JWT token alma ve yenileme"},
            {"name": "users", "description": "Kullanıcı profili"},
            {"name": "pharmacies", "description": "Eczane yönetimi"},
            {"name": "kiosks", "description": "Kiosk yönetimi"},
            {"name": "products", "description": "Ürün kataloğu"},
            {"name": "analytics", "description": "Anket ve gösterim analitiği"},
            {"name": "campaigns", "description": "Kampanya yönetimi"},
        ],
    }


# ─── Loglama: Yapısal JSON + Rotasyonlu Dosya ────────────────────────────────
# ElasticSearch/Logstash gibi ağır araçlar yerine; uygulama hatalarını ve
# isteklerini standart yapısal JSON olarak rotasyonlu dosyalara yazıyoruz.
# Audit (iş-mantığı) logları PostgreSQL'deki AuditLog modelinde tutulur.

LOG_DIR = Path(config("DJANGO_LOG_DIR", default=str(BASE_DIR / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_LEVEL = config("DJANGO_LOG_LEVEL", default="INFO" if not DEBUG else "INFO")
LOG_MAX_BYTES = config("DJANGO_LOG_MAX_BYTES", default=10 * 1024 * 1024, cast=int)  # 10 MB
LOG_BACKUP_COUNT = config("DJANGO_LOG_BACKUP_COUNT", default=5, cast=int)


class _JsonFormatter(logging.Formatter):
    """Hafif, bağımlılıksız JSON satır formatlayıcı."""

    _RESERVED = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "asctime", "message",
    }

    def format(self, record: logging.LogRecord) -> str:  # pragma: no cover
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key in self._RESERVED or key.startswith("_"):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except TypeError:
                payload[key] = repr(value)
        return json.dumps(payload, ensure_ascii=False)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": _JsonFormatter},
        "console": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "level": LOG_LEVEL,
        },
        "app_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
            "formatter": "json",
            "level": "INFO",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "error.log"),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
            "formatter": "json",
            "level": "ERROR",
        },
        "request_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "request.log"),
            "maxBytes": LOG_MAX_BYTES,
            "backupCount": LOG_BACKUP_COUNT,
            "encoding": "utf-8",
            "formatter": "json",
            "level": "WARNING",  # 4xx/5xx
        },
    },
    "root": {
        "handlers": ["console", "app_file", "error_file"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console", "app_file", "error_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # 5xx ve unhandled exception'lar buraya düşer.
        "django.request": {
            "handlers": ["console", "request_file", "error_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "eisa": {
            "handlers": ["console", "app_file", "error_file"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

