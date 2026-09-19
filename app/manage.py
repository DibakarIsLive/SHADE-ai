#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main() -> None:
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - Django reports the actionable error.
        raise ImportError(
            "Django is unavailable. Activate app/.venv or run `make install` from app/."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
