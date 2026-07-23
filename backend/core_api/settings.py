"""
Django ayarları — E-İSA Merkezi API.

KVKK uyumu: tüm kişisel olmayan demografik veriler anonim toplanır.
Loglama: dosya yerine JSON stdout üretilir; toplama Kubernetes node collector
(Grafana Alloy) tarafından yapılır. Detay: docs/operations/logging.md.
"""
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
    "django_apscheduler",
    # Yerel uygulamalar
    "apps.core",
    "apps.lookups",
    "apps.users",
    "apps.pharmacies",
    "apps.products",
    "apps.analytics",
    "apps.campaigns",
    "apps.audit",
    "apps.kiosk_api",
]

MIDDLEWARE = [
    "apps.core.logging.middleware.CorrelationIdMiddleware",
    "apps.core.logging.middleware.RequestLoggingMiddleware",
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

# DB_* (yeni K8s contract) → POSTGRES_* (geri uyumluluk) fallback.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME":     config("DB_NAME",     default=config("POSTGRES_DB",       default="eisa")),
        "USER":     config("DB_USER",     default=config("POSTGRES_USER",     default="eisa")),
        "PASSWORD": config("DB_PASSWORD", default=config("POSTGRES_PASSWORD", default="eisa" if DEBUG else "")),
        "HOST":     config("DB_HOST",     default=config("POSTGRES_HOST",     default="localhost")),
        "PORT":     config("DB_PORT",     default=config("POSTGRES_PORT",     default="5432")),
        # PgBouncer transaction pooling ile uyumlu olması için connection-level
        # özellikleri kapalı tutuyoruz; uzun süreli connection açmıyoruz.
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=0, cast=int),
    }
}
if not DEBUG and (not DATABASES["default"]["PASSWORD"] or DATABASES["default"]["PASSWORD"] == "eisa"):
    raise ImproperlyConfigured(
        "DB_PASSWORD üretimde güçlü ve rastgele bir değere ayarlanmalıdır."
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
        # Log ingestion endpoint'leri — kötüye kullanımı engelle.
        "kiosk_diagnostic": config("THROTTLE_KIOSK_DIAGNOSTIC", default="60/min"),
        "client_event": config("THROTTLE_CLIENT_EVENT", default="30/min"),
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

# ─── Kiosk IoT Kimlik Dogrulama ──────────────────────────────────────────────
# KIOSK_FLEET_KEY   : Tum kiosk cihazlarin gonderdigi ortak header (X-Kiosk-Key).
#                     Backend, bu olmayan istekleri kiosk istegi olarak isleme almaz.
# KIOSK_PROVISIONING_SECRET : HMAC-SHA256 provision imzasi icin ortak sir (yalniz bootstrap).
#                     Kiosk + backend'de ayni deger olmali.
KIOSK_FLEET_KEY              = config("KIOSK_FLEET_KEY", default="dev_fleet_key")
KIOSK_PROVISIONING_SECRET    = config("KIOSK_PROVISIONING_SECRET", default="dev_provisioning_secret")

# ─── JWT httpOnly Çerez Ayarları (SEC-002) ──────────────────────────────────
JWT_AUTH_COOKIE = config("JWT_AUTH_COOKIE", default="eisa_access")
JWT_REFRESH_COOKIE = config("JWT_REFRESH_COOKIE", default="eisa_refresh")
JWT_COOKIE_SAMESITE = config("JWT_COOKIE_SAMESITE", default="Strict")
JWT_COOKIE_SECURE = config("JWT_COOKIE_SECURE", default=not DEBUG, cast=bool)
JWT_COOKIE_DOMAIN = config("JWT_COOKIE_DOMAIN", default=None)
if JWT_COOKIE_DOMAIN == "":
    JWT_COOKIE_DOMAIN = None

# CORS_ALLOWED_ORIGINS (K8s contract) → DJANGO_CORS_ORIGINS (legacy) fallback.
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default=config("DJANGO_CORS_ORIGINS", default=""),
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

# S3 / RustFS — yeni K8s contract (S3_*) eski isimlere (RUSTFS_*) fallback eder.
S3_ENDPOINT             = config("S3_ENDPOINT",          default=config("RUSTFS_ENDPOINT",   default="localhost:9000"))
S3_ACCESS_KEY           = config("S3_ACCESS_KEY",        default=config("RUSTFS_ACCESS_KEY", default="admin"))
S3_SECRET_KEY           = config("S3_SECRET_KEY",        default=config("RUSTFS_SECRET_KEY", default="admin1234"))
S3_BUCKET               = config("S3_BUCKET",            default=config("RUSTFS_BUCKET_NAME", default="dev"))
S3_REGION               = config("S3_REGION",            default="us-east-1")
S3_FORCE_PATH_STYLE     = config("S3_FORCE_PATH_STYLE",  default=True, cast=bool)
S3_SECURE               = config("S3_SECURE",            default=config("RUSTFS_SECURE", default=False, cast=bool), cast=bool)
S3_PRESIGNED_URL_TTL_MINUTES = config("S3_PRESIGNED_URL_TTL_MINUTES",
                                       default=config("RUSTFS_PRESIGNED_URL_TTL_MINUTES", default=60, cast=int),
                                       cast=int)

# Kalıcı medya erişim URL'si tabanı (bucket adını dahil edin).
# Format: https://<endpoint>/<bucket>  (örn. https://files.eisa.com.tr/eisa-files)
# Sözleşme: media_url = S3_PUBLIC_BASE_URL + "/" + object_key
# Boş bırakılırsa DOOH_PERSISTENT_MEDIA_URL=True iken ImproperlyConfigured üretilir.
# Production deploy YAML'ında S3_ENDPOINT=files.eisa.com.tr, S3_BUCKET=eisa-files
# olduğundan: S3_PUBLIC_BASE_URL=https://files.eisa.com.tr/eisa-files
S3_PUBLIC_BASE_URL = config("S3_PUBLIC_BASE_URL", default="")

# DOOH kalıcı medya URL feature flag.
DOOH_PERSISTENT_MEDIA_URL = config("DOOH_PERSISTENT_MEDIA_URL", default=False, cast=bool)

# DOOH Horizon — rolling horizon gün sayısı (bugün dahil). Operasyonel ayar.
# Default 3: bugün, bugün+1, bugün+2.
DOOH_HORIZON_DAYS = config("DOOH_HORIZON_DAYS", default=3, cast=int)

# NOT (Faz 7): DOOH_ENGINE_V2, DOOH_ASYNC_QUEUE, DOOH_KIOSK_ACK flag'leri
# kaldırıldı. V2 engine, async queue ve kiosk ACK canonical ve her zaman aktiftir.
# Ortam değişkenlerinden okumak hataya neden olmaz (okunmaz, ignore edilir).

# Geri uyumlu alias'lar (mevcut kod RUSTFS_* okuyabilir).
RUSTFS_ENDPOINT                   = S3_ENDPOINT
RUSTFS_ACCESS_KEY                 = S3_ACCESS_KEY
RUSTFS_SECRET_KEY                 = S3_SECRET_KEY
RUSTFS_BUCKET_NAME                = S3_BUCKET
RUSTFS_SECURE                     = S3_SECURE
RUSTFS_PRESIGNED_URL_TTL_MINUTES  = S3_PRESIGNED_URL_TTL_MINUTES

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


# ─── Loglama: Yapısal JSON stdout (Kubernetes standardı) ─────────────────────
# Uygulama logları hiçbir dosyaya yazılmaz. Grafana Alloy container stdout/stderr
# akışlarını okuyarak Loki'ye iletir. Detay: docs/operations/logging.md.
# İş kayıtları (AuditLog, OturumLogu, PlayLog vb.) etkilenmez; onlar
# PostgreSQL'de kalmaya devam eder.

SERVICE_NAME = config("SERVICE_NAME", default="eisa-backend")
APP_ENV = config(
    "APP_ENV",
    default=config("EISA_ENVIRONMENT", default="development" if DEBUG else "production"),
)
APP_VERSION = config("APP_VERSION", default="0.0.0")

LOG_LEVEL = config("LOG_LEVEL", default="DEBUG" if DEBUG else "INFO").upper()
_default_log_format = "console" if DEBUG else "json"
LOG_FORMAT = config("LOG_FORMAT", default=_default_log_format).lower()
if LOG_FORMAT not in ("json", "console"):
    LOG_FORMAT = "json"

_root_handler = "console_json" if LOG_FORMAT == "json" else "console_readable"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "apps.core.logging.formatters.JsonFormatter",
            "service_name": SERVICE_NAME,
            "environment": APP_ENV,
            "version": APP_VERSION,
        },
        "readable": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": LOG_LEVEL,
        },
        "console_readable": {
            "class": "logging.StreamHandler",
            "formatter": "readable",
            "level": LOG_LEVEL,
        },
    },
    "root": {
        "handlers": [_root_handler],
        "level": LOG_LEVEL,
    },
    "loggers": {
        # Django kendi zaten AccessLog/Server log üretir; biz request lifecycle
        # middleware ile tek satırlık completion log üretiyoruz. `django.server`
        # yalnızca development runserver çıktısı içindir.
        "django": {
            "handlers": [_root_handler],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            # 4xx/5xx için handler zaten kendi request middleware'imiz tarafından
            # üretiliyor; Django'nun kendi warning'lerini INFO'a bastırmıyoruz ama
            # aynı hatayı iki kez yazmasını engellemek için sadece warning+ tutuyoruz.
            "handlers": [_root_handler],
            "level": "WARNING",
            "propagate": False,
        },
        "django.server": {
            "handlers": [_root_handler],
            "level": "INFO" if DEBUG else "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            # Prod'da SQL parametrelerinin loglanmasını engelle.
            "handlers": [_root_handler],
            "level": "WARNING",
            "propagate": False,
        },
        "eisa": {
            "handlers": [_root_handler],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "eisa.request": {
            "handlers": [_root_handler],
            "level": "INFO",
            "propagate": False,
        },
        "eisa.errors": {
            "handlers": [_root_handler],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ── APScheduler (django-apscheduler) ─────────────────────────────────────────
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25  # saniye
