"""Bridge settings. Every secret comes from the environment (.env)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=None):
    return os.environ.get(name, default)


DEBUG = env("DJANGO_DEBUG", "0") == "1"
# The fallback exists only so tests run without a .env; compose requires the real one.
SECRET_KEY = env("DJANGO_SECRET_KEY") or "insecure-test-only-key"
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "core",
    "firefly",
    "ingest",
    "mail",
    "statements",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

if env("BRIDGE_DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": env("BRIDGE_DB_HOST"),
            "PORT": env("BRIDGE_DB_PORT", "5432"),
            "NAME": env("BRIDGE_DB_NAME", "bridge"),
            "USER": env("BRIDGE_DB_USER", "bridge"),
            "PASSWORD": env("BRIDGE_DB_PASSWORD", ""),
        }
    }
else:  # tests and local tooling without the stack
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL")
if REDIS_URL:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}}
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_TZ = True

# Request-size limit (SPEC security rules). 256 KiB is far above any SMS or email alert.
DATA_UPLOAD_MAX_MEMORY_SIZE = 256 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["core.auth.BridgeTokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "20/min", "user": "120/min"},
    "UNAUTHENTICATED_USER": None,
}

# Single-user API token. Clients send:  Authorization: Bearer <token>
BRIDGE_API_TOKEN = env("BRIDGE_API_TOKEN", "")

FIREFLY_BASE_URL = env("FIREFLY_BASE_URL", "http://firefly:8080")
FIREFLY_ACCESS_TOKEN = env("FIREFLY_ACCESS_TOKEN", "")
FIREFLY_TIMEOUT_SECONDS = 15

# --- Ingestion (M2) ---
# Shared with the SMS forwarder; it signs each request body (X-Signature, HMAC-SHA-256).
BRIDGE_SMS_HMAC_SECRET = env("BRIDGE_SMS_HMAC_SECRET", "")
INGEST_PROFILE_DIRS = [BASE_DIR / "ingest" / "profiles"]
INGEST_EMAIL_PROFILE_DIRS = [BASE_DIR / "ingest" / "profiles" / "email"]
# The owner's own UPI IDs. Money to or from one of them moves between own accounts,
# so it is never counted as spend or income on its own.
# For banks whose SMS never name the account: "profile=last4,profile=last4" (e.g. "federal=1234").
INGEST_DEFAULT_ACCOUNTS = dict(
    pair.strip().split("=", 1) for pair in env("BRIDGE_DEFAULT_ACCOUNTS", "").split(",") if "=" in pair
)
INGEST_OWN_VPAS = {v.strip().lower() for v in env("BRIDGE_OWN_VPAS", "").split(",") if v.strip()}
INGEST_SETTLE_SECONDS = int(env("INGEST_SETTLE_SECONDS", "600"))  # wait for the other half of a transfer
INGEST_SAME_PAYMENT_WINDOW_MINUTES = 30
INGEST_TRANSFER_WINDOW_MINUTES = 180
INGEST_REFERENCE_WINDOW_DAYS = 7
BALANCE_CONFIRMED_HOURS = 72  # a bank-reported balance older than this is "stale"

# --- Mail and statements (M3) ---
# Key for secrets stored in the database (Gmail tokens, statement passwords). Lives only in .env.
BRIDGE_ENCRYPTION_KEY = env("BRIDGE_ENCRYPTION_KEY", "")
# Nothing before this date is posted to the ledger (opening balances cover it).
INGEST_LEDGER_START = env("INGEST_LEDGER_START", "2026-11-01")
GMAIL_POLL_MINUTES = int(env("GMAIL_POLL_MINUTES", "10"))
GMAIL_REQUEST_PAUSE_SECONDS = float(env("GMAIL_REQUEST_PAUSE_SECONDS", "0.25"))
STATEMENT_DIR = Path(env("STATEMENT_DIR", "/data/statements"))

CELERY_BROKER_URL = REDIS_URL or "memory://"
CELERY_RESULT_BACKEND = REDIS_URL or "cache+memory://"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_BEAT_SCHEDULE = {
    "ingest-sweep": {"task": "ingest.tasks.sweep", "schedule": 60.0},
    "gmail-poll": {"task": "mail.tasks.poll_all", "schedule": GMAIL_POLL_MINUTES * 60.0},
    "statements": {"task": "statements.tasks.process_pending", "schedule": 3600.0},
}

# Log metadata only. Message bodies, account numbers and tokens are never logged.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"httpx": {"level": "WARNING"}},
}
