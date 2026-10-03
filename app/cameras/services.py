"""Camera persistence and response mapping services."""

from __future__ import annotations

from datetime import datetime, timezone

from config.database import connect_mongodb
from cameras.documents import Camera


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def serialize_camera(camera: Camera) -> dict:
    return {
        "camera_id": camera.camera_id,
        "name": camera.name,
        "source_type": camera.source_type,
        "source_uri": camera.source_uri,
        "location": camera.location,
        "enabled": camera.enabled,
        "status": camera.status,
        "created_at": _timestamp(camera.created_at),
        "updated_at": _timestamp(camera.updated_at),
    }


def get_camera(camera_id: str) -> Camera | None:
    """Load one existing camera configuration for a standalone worker."""
    connect_mongodb()
    return Camera.objects(camera_id=camera_id).first()


def list_cameras(limit: int = 50) -> list[dict]:
    connect_mongodb()
    return [serialize_camera(camera) for camera in Camera.objects.order_by("-created_at").limit(limit)]


def create_camera(data: dict) -> dict:
    connect_mongodb()
    camera = Camera(**data)
    camera.save()
    return serialize_camera(camera)
