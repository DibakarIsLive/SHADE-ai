#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

from __future__ import annotations

import os
import sys


FORCE_FLAG = "--force"
DIAGNOSTIC_MODE_ENV = "SHADE_AI_DIAGNOSTIC_MODE"


def _runserver_index(argv: list[str]) -> int | None:
    """Return the runserver command index, or None for other commands."""
    try:
        return argv.index("runserver", 1)
    except ValueError:
        return None


def _prepare_runserver_arguments(argv: list[str]) -> tuple[list[str], bool]:
    """Remove SHADE-ai's force flag before Django parses runserver options."""
    command_index = _runserver_index(argv)
    if command_index is None:
        return list(argv), False

    force = False
    cleaned: list[str] = []
    for index, argument in enumerate(argv):
        if index > command_index and argument == FORCE_FLAG:
            force = True
            continue
        cleaned.append(argument)
    return cleaned, force


def _require_mongodb(force: bool = False) -> None:
    """Require the configured MongoDB service for normal runserver startup."""
    if force:
        return

    from config.database import database_available

    if database_available():
        return

    raise SystemExit(
        "MongoDB startup check failed. Start the configured MongoDB server before "
        "running the SHADE-ai API. To explicitly bypass this development check, "
        "use `python manage.py runserver --force` or `make dev -- --force`."
    )


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - Django reports the actionable error.
        raise ImportError(
            "Django is unavailable. Activate app/.venv or run `make install` from app/."
        ) from exc

    argv, force = _prepare_runserver_arguments(sys.argv)
    sys.argv[:] = argv
    if _runserver_index(argv) is not None:
        # Django's autoreloader starts a child process. Preserve the explicit
        # command-line decision across that process without exposing a custom
        # option to Django's own argument parser.
        force = force or os.environ.get(DIAGNOSTIC_MODE_ENV) == "1"
        if force:
            os.environ[DIAGNOSTIC_MODE_ENV] = "1"
        _require_mongodb(force=force)

    execute_from_command_line(argv)


if __name__ == "__main__":
    main()
