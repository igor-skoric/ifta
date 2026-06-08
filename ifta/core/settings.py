from pathlib import Path
import ipaddress
import os
import sys

from django.core.exceptions import ImproperlyConfigured

from core.env import env_bool, env_list

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv():
    """Load KEY=value lines from BASE_DIR/.env if present (no extra dependency)."""
    env_file = BASE_DIR / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

_DEBUG_DEFAULT = env_bool("DJANGO_DEBUG", default=True)
DEBUG = _DEBUG_DEFAULT

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-j633n(o*au4ljzmqfnp4(m65e-yanmq)ax-0b6*8lgoo-x@uoc",
)
if not DEBUG and SECRET_KEY.startswith("django-insecure"):
    raise ImproperlyConfigured(
        "Set DJANGO_SECRET_KEY to a unique random value before running with DJANGO_DEBUG=false."
    )

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost,ifta.rs.itbranch.rs,www.ifta.rs.itbranch.rs,192.168.0.30",
)

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")
if not CSRF_TRUSTED_ORIGINS and not DEBUG:
    _csrf_hosts = []
    for host in ALLOWED_HOSTS:
        if not host or host.startswith("."):
            continue
        try:
            ipaddress.ip_address(host)
        except ValueError:
            _csrf_hosts.append(f"https://{host}")
    CSRF_TRUSTED_ORIGINS = _csrf_hosts


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ifta.apps.IftaConfig',
    'tailwind',
    'theme',
    'statistic',
    'rest_framework',
    'office',
    'dispatch',
    'accounts',
    'leave',
    'samsara',
]

# Universal domain-oriented app split
DOMAIN_APPS = ("ifta", "statistics", "office", "dispatch", "leave", "samsara")

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.DevClearHstsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.universal_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        # SQLite često "database is locked" pri paralelnom pristupu; timeout čeka oslobađanje umesto trenutnog pada.
        'OPTIONS': {
            'timeout': 30,
        },
    }
}

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Relative to static/ — stavi PDF ovde za Office map stranicu (inače se koristi SVG fallback).
OFFICE_FLOOR_PLAN_PDF = os.getenv("OFFICE_FLOOR_PLAN_PDF", "office/office_floor_plan.pdf")

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

# US Central (CST/CDT). Override via DJANGO_TIME_ZONE if needed.
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "America/Chicago")
STATISTIC_WEEK_TIMEZONE = TIME_ZONE

USE_I18N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING_DIR = os.path.join(BASE_DIR, "logs")  # Kreiraj folder za logove
if not os.path.exists(LOGGING_DIR):
    os.makedirs(LOGGING_DIR)

DATA_UPLOAD_MAX_NUMBER_FIELDS = int(os.getenv("DATA_UPLOAD_MAX_NUMBER_FIELDS", "10000"))
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("DATA_UPLOAD_MAX_MEMORY_SIZE", str(10 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("FILE_UPLOAD_MAX_MEMORY_SIZE", str(5 * 1024 * 1024)))
TAILWIND_APP_NAME = 'theme'
_default_npm = (
    r"C:\Program Files\nodejs\npm.cmd" if sys.platform == "win32" else "npm"
)
NPM_BIN_PATH = os.getenv("NPM_BIN_PATH", _default_npm)

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

AUTHENTICATION_BACKENDS = [
    "accounts.auth_backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@ifta.local")

SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    BASE_DIR / "statistic" / "secrets" / "service_account.json"
)

# Statistics API base URL is configurable to support future extraction.
STATISTICS_API_BASE_URL = os.getenv("STATISTICS_API_BASE_URL", "/api/statistic").rstrip("/")
SAMSARA_API_BASE_URL = os.getenv("SAMSARA_API_BASE_URL", "https://api.samsara.com").rstrip("/")
SAMSARA_API_TOKEN = os.getenv("SAMSARA_API_TOKEN", "")
SAMSARA_API_TIMEOUT_SECONDS = int(os.getenv("SAMSARA_API_TIMEOUT_SECONDS", "20"))
SAMSARA_VEHICLES_ENDPOINT = os.getenv("SAMSARA_VEHICLES_ENDPOINT", "/fleet/vehicles")
SAMSARA_DRIVERS_ENDPOINT = os.getenv("SAMSARA_DRIVERS_ENDPOINT", "/fleet/drivers")
# Trips su još na legacy API-ju: GET .../v1/fleet/trips (vehicleId + startMs + endMs).
SAMSARA_TRIPS_ENDPOINT = os.getenv("SAMSARA_TRIPS_ENDPOINT", "/v1/fleet/trips")
SAMSARA_TRIPS_DAYS_BACK = int(os.getenv("SAMSARA_TRIPS_DAYS_BACK", "14"))
# Pri inkrementalnom syncu: startMs = poslednji uspešni endMs minus ovaj overlap (ms).
SAMSARA_TRIPS_INCREMENTAL_OVERLAP_MS = int(
    os.getenv("SAMSARA_TRIPS_INCREMENTAL_OVERLAP_MS", str(2 * 3600 * 1000))
)
# Pauza između GET /v1/fleet/trips po vozilu — smanjuje Samsara 5xx (npr. Too many connections / 1040).
SAMSARA_TRIPS_INTER_REQUEST_DELAY_SECONDS = float(
    os.getenv("SAMSARA_TRIPS_INTER_REQUEST_DELAY_SECONDS", "0.25")
)
# Kratki retry na privremene 5xx od API-ja (npr. preopterećenje).
SAMSARA_API_RETRY_MAX = int(os.getenv("SAMSARA_API_RETRY_MAX", "4"))
SAMSARA_LOCATIONS_FEED_ENDPOINT = os.getenv(
    "SAMSARA_LOCATIONS_FEED_ENDPOINT", "/fleet/vehicles/locations/feed"
)
SAMSARA_VEHICLE_STATS_ENDPOINT = os.getenv(
    "SAMSARA_VEHICLE_STATS_ENDPOINT", "/fleet/vehicles/stats"
)
SAMSARA_GPS_CACHE_SECONDS = int(os.getenv("SAMSARA_GPS_CACHE_SECONDS", "30"))

if not os.path.exists(SERVICE_ACCOUNT_FILE):
    msg = f"Service account file not found: {SERVICE_ACCOUNT_FILE}"
    if DEBUG:
        print(f"WARNING: {msg}", file=sys.stderr)
    else:
        raise ImproperlyConfigured(msg)

# --- Production / HTTPS hardening (enable via env on the server) ---
_RUNNING_DEV_SERVER = any(arg == "runserver" for arg in sys.argv)
USE_HTTPS = env_bool("DJANGO_USE_HTTPS", default=not DEBUG)
if _RUNNING_DEV_SERVER:
    # runserver speaks HTTP only; SECURE_SSL_REDIRECT → broken https://127.0.0.1:8000/
    USE_HTTPS = False
    # Avoid treating proxied/local requests as HTTPS when testing with production .env
    TRUST_X_FORWARDED_FOR = False
else:
    TRUST_X_FORWARDED_FOR = env_bool("TRUST_X_FORWARDED_FOR", default=False)
if TRUST_X_FORWARDED_FOR:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "SAMEORIGIN"
    SESSION_COOKIE_SECURE = USE_HTTPS
    CSRF_COOKIE_SECURE = USE_HTTPS
    if USE_HTTPS:
        SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
        SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
        SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
        SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", default=False)

# TV / wall display access to statistics pages and read-only APIs
STATISTICS_TV_PUBLIC_READ = env_bool("STATISTICS_TV_PUBLIC_READ", default=False)
STATISTICS_TV_TOKEN = os.getenv("STATISTICS_TV_TOKEN", "")
STATISTICS_TV_TOKEN_QUERY_PARAM = os.getenv("STATISTICS_TV_TOKEN_QUERY_PARAM", "tv_token")
STATISTICS_TV_ALLOWED_IPS = env_list(
    "STATISTICS_TV_ALLOWED_IPS",
    "127.0.0.1,::1,192.168.0.30",
)

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "error": {
            "format": "{levelname} {asctime} {pathname}:{lineno} {message}",
            "style": "{",
        },
    },
    "handlers": {
        # Handler za ERROR logove
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "errors.log"),
            "maxBytes": 5 * 1024 * 1024,  # 5MB po fajlu
            "backupCount": 3,  # Čuva poslednja 3 log fajla
            "formatter": "error",
        },
        # Handler za INFO logove
        "info_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGGING_DIR, "info.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["error_file", "info_file"],
            "level": "INFO",  # Hvatamo i INFO i ERROR logove
            "propagate": True,
        },
        "samsara": {
            "handlers": ["info_file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

