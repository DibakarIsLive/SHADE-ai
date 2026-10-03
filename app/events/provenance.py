"""Validation and normalization for structured event provenance."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from events.documents import EVENT_SOURCE_TYPES, EventProvenance


_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
_PROVENANCE_FIELDS = {
    "provider",
    "model_identifier",
    "model_version",
    "artifact_sha256",
    "source_type",
    "camera_id",
    "processed_at",
}


class EventProvenanceValidationError(ValueError):
    """Supplied event provenance is incomplete, inconsistent, or malformed."""


def build_event_provenance(
    value: Mapping[str, Any] | None,
    *,
    event_camera_id: Any,
) -> EventProvenance | None:
    """Validate caller-supplied provenance and construct its typed document.

    ``None`` deliberately represents an event from a legacy path whose runtime
    provenance is unavailable. No model identity, version, or digest is inferred.
    """
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise EventProvenanceValidationError("Event provenance must be an object or null.")

    unknown_fields = set(value) - _PROVENANCE_FIELDS
    if unknown_fields:
        raise EventProvenanceValidationError("Event provenance contains unsupported fields.")

    provider = value.get("provider")
    if not isinstance(provider, str) or not provider.strip() or len(provider.strip()) > 120:
        raise EventProvenanceValidationError("Event provenance provider must be a non-empty name of at most 120 characters.")

    model_identifier = _optional_nonempty_string(
        value.get("model_identifier"), "model_identifier", max_length=200
    )
    model_version = _optional_nonempty_string(
        value.get("model_version"), "model_version", max_length=120
    )

    artifact_sha256 = value.get("artifact_sha256")
    if artifact_sha256 is not None:
        if not isinstance(artifact_sha256, str) or not _SHA256_PATTERN.fullmatch(artifact_sha256):
            raise EventProvenanceValidationError(
                "Event provenance artifact_sha256 must be a 64-character hexadecimal SHA-256 digest or null."
            )
        artifact_sha256 = artifact_sha256.lower()

    source_type = value.get("source_type")
    if source_type not in EVENT_SOURCE_TYPES:
        raise EventProvenanceValidationError("Event provenance source_type is unsupported.")

    camera_id = value.get("camera_id")
    if not isinstance(camera_id, str) or not camera_id.strip() or len(camera_id.strip()) > 120:
        raise EventProvenanceValidationError("Event provenance camera_id must be a non-empty identity of at most 120 characters.")
    camera_id = camera_id.strip()
    if (
        not isinstance(event_camera_id, str)
        or not event_camera_id.strip()
        or camera_id != event_camera_id.strip()
    ):
        raise EventProvenanceValidationError(
            "Event provenance camera_id must match the event camera_id."
        )

    processed_at = value.get("processed_at")
    if (
        not isinstance(processed_at, datetime)
        or processed_at.tzinfo is None
        or processed_at.utcoffset() is None
    ):
        raise EventProvenanceValidationError(
            "Event provenance processed_at must be a timezone-aware datetime."
        )

    return EventProvenance(
        provider=provider.strip(),
        model_identifier=model_identifier,
        model_version=model_version,
        artifact_sha256=artifact_sha256,
        source_type=source_type,
        camera_id=camera_id,
        processed_at=processed_at,
    )


def _optional_nonempty_string(value: Any, field_name: str, *, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_length:
        raise EventProvenanceValidationError(
            f"Event provenance {field_name} must be a non-empty string of at most {max_length} characters or null."
        )
    return value.strip()
