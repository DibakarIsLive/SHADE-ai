"""Shared Django settings for every SHADE-ai environment."""

from pathlib import Path
import os

from dotenv import load_dotenv


# app/ is the Django project root.
BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=False)


def env_bool(name: str, default: bool = False) -> bool:
    """Read a human-friendly boolean environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    """Read a comma-separated environment variable as a clean list."""
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# -----------------------------------------------------------------------------
# Core Django settings
# -----------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "shade-ai-development-only-key")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DJANGO_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "channels",
    "corsheaders",
    "rest_framework",
]

LOCAL_APPS = [
    "core",
    "cameras",
    "events",
    "monitoring",
]

INSTALLED_APPS = [*DJANGO_APPS, *THIRD_PARTY_APPS, *LOCAL_APPS]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

# SHADE-ai returns JSON and does not render Django templates.
TEMPLATES = []

# Django's relational ORM is intentionally disabled. MongoEngine owns the
# application documents, avoiding an accidental SQLite database in the repo.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.dummy",
    }
}

# -----------------------------------------------------------------------------
# MongoDB / MongoEngine
# -----------------------------------------------------------------------------
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "shade_ai")
MONGODB_SERVER_SELECTION_TIMEOUT_MS = int(
    os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "500")
)
MONGODB_CONNECT_TIMEOUT_MS = int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "500"))
MONGODB_SOCKET_TIMEOUT_MS = int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "1000"))

# -----------------------------------------------------------------------------
# Internationalization, static files, and API behavior
# -----------------------------------------------------------------------------
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "en-us")
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Calcutta")
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
CORS_ALLOW_CREDENTIALS = env_bool("CORS_ALLOW_CREDENTIALS", False)

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": os.getenv("API_ANON_RATE", "120/min")},
}

# -----------------------------------------------------------------------------
# Monitoring and evidence boundaries
# -----------------------------------------------------------------------------
MONITORING_MODE = os.getenv("MONITORING_MODE", "synthetic")
VISION_DEVICE = os.getenv("VISION_DEVICE", "cpu").strip().lower()
VISION_MODEL_PATH = Path(
    os.getenv("VISION_MODEL_PATH", str(BASE_DIR / "model-artifacts/vision/rtmo-s/model.onnx"))
).expanduser()
VISION_CONFIDENCE_THRESHOLD = float(os.getenv("VISION_CONFIDENCE_THRESHOLD", "0.25"))
VISION_KEYPOINT_THRESHOLD = float(os.getenv("VISION_KEYPOINT_THRESHOLD", "0.2"))
VISION_PROVIDER = os.getenv("VISION_PROVIDER", "development-null").strip().lower()
CAMERA_FRAME_INTERVAL_SECONDS = float(os.getenv("CAMERA_FRAME_INTERVAL_SECONDS", "0.1"))
EVIDENCE_DIR = BASE_DIR / os.getenv("EVIDENCE_DIR", "runtime/evidence")
EVIDENCE_RETENTION_DAYS = int(os.getenv("EVIDENCE_RETENTION_DAYS", "7"))
NOTIFICATION_MODE = os.getenv("NOTIFICATION_MODE", "dry-run")
NOTIFICATION_RECIPIENT = os.getenv("NOTIFICATION_RECIPIENT", "")

if VISION_PROVIDER not in {"development-null", "rtmo-s"}:
    raise ValueError("VISION_PROVIDER must be 'development-null' or 'rtmo-s'")
if not 0.0 <= VISION_CONFIDENCE_THRESHOLD <= 1.0:
    raise ValueError("VISION_CONFIDENCE_THRESHOLD must be between 0 and 1")
if not 0.0 <= VISION_KEYPOINT_THRESHOLD <= 1.0:
    raise ValueError("VISION_KEYPOINT_THRESHOLD must be between 0 and 1")
if VISION_DEVICE not in {"cpu", "gpu"}:
    raise ValueError("VISION_DEVICE must be 'cpu' or 'gpu'")
if CAMERA_FRAME_INTERVAL_SECONDS <= 0:
    raise ValueError("CAMERA_FRAME_INTERVAL_SECONDS must be positive")
if EVIDENCE_RETENTION_DAYS < 1:
    raise ValueError("EVIDENCE_RETENTION_DAYS must be positive")

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.FileHandler",
            "filename": LOG_DIR / "shade-ai.log",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console", "file"], "level": LOG_LEVEL},
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
