"""Emergency event persistence and response mapping services."""

from __future__ import annotations

from datetime import datetime, timezone

from config.database import connect_mongodb
from events.documents import EmergencyEvent


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def serialize_event(event: EmergencyEvent) -> dict:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "severity": event.severity,
        "status": event.status,
        "camera_id": event.camera_id,
        "track_id": event.track_id,
        "confidence": event.confidence,
        "duration_seconds": event.duration_seconds,
        "frame_count": event.frame_count,
        "evidence_uri": event.evidence_uri,
        "context": event.context,
        "occurred_at": _timestamp(event.occurred_at),
        "created_at": _timestamp(event.created_at),
    }


def list_events(limit: int = 50) -> list[dict]:
    connect_mongodb()
    return [
        serialize_event(event)
        for event in EmergencyEvent.objects.order_by("-occurred_at").limit(limit)
    ]


def create_event(data: dict) -> dict:
    connect_mongodb()
    event = EmergencyEvent(**data)
    event.save()
    return serialize_event(event)
