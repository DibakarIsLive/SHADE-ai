"""Small line-oriented lifecycle protocol between a supervised worker and Django."""

from __future__ import annotations

import json
from typing import Any, TextIO


LIFECYCLE_PREFIX = "SHADE_WORKER_EVENT "


def emit_lifecycle_event(stream: TextIO, event: str, **payload: Any) -> None:
    """Write one flushed, machine-readable lifecycle event to the worker's stdout."""
    message = {"event": event, **payload}
    stream.write(f"{LIFECYCLE_PREFIX}{json.dumps(message, separators=(',', ':'))}\n")
    stream.flush()
