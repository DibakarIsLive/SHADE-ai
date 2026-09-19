"""Lazy MongoDB connection and bounded health diagnostics."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from mongoengine import connect, get_connection
from mongoengine.connection import ConnectionFailure
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError


LOGGER = logging.getLogger(__name__)
CONNECTION_ALIAS = "default"


def connect_mongodb() -> Any:
    """Create the shared MongoEngine connection without blocking on startup."""
    try:
        return get_connection(alias=CONNECTION_ALIAS)
    except ConnectionFailure:
        return connect(
            db=settings.MONGODB_DATABASE,
            host=settings.MONGODB_URI,
            alias=CONNECTION_ALIAS,
            connect=False,
            serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
            connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
            socketTimeoutMS=settings.MONGODB_SOCKET_TIMEOUT_MS,
        )


def check_mongodb() -> dict[str, Any]:
    """Ping MongoDB with a bounded timeout and return a safe public report."""
    try:
        connection = connect_mongodb()
        connection.admin.command("ping")
        return {
            "available": True,
            "status": "healthy",
            "database": settings.MONGODB_DATABASE,
        }
    except (ConnectionFailure, ServerSelectionTimeoutError, PyMongoError) as exc:
        LOGGER.warning("MongoDB health check failed: %s", exc)
        return {
            "available": False,
            "status": "unavailable",
            "database": settings.MONGODB_DATABASE,
            "detail": "MongoDB is not reachable; persistence is currently degraded.",
        }


def database_available() -> bool:
    """Return whether MongoDB responds to a bounded ping."""
    return bool(check_mongodb()["available"])
