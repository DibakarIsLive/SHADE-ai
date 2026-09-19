"""Local development settings for SHADE-ai."""

from .base import *  # noqa: F403,F401


DEBUG = True
ALLOWED_HOSTS = sorted({*ALLOWED_HOSTS, "127.0.0.1", "localhost", "testserver"})  # noqa: F405
CORS_ALLOWED_ORIGINS = sorted(  # noqa: F405
    {
        *CORS_ALLOWED_ORIGINS,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    }
)
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")  # noqa: F405
