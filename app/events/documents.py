"""MongoEngine documents for verified activity and emergency events."""

from datetime import datetime
from uuid import uuid4

from mongoengine import (
    DateTimeField,
    DictField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    FloatField,
    IntField,
    StringField,
)


EVENT_SOURCE_TYPES = ("webcam", "rtsp", "video_file", "synthetic")


class EventProvenance(EmbeddedDocument):
    """Runtime identity for the source and vision components behind an event."""

    provider = StringField(required=True, max_length=120)
    model_identifier = StringField(null=True, default=None, max_length=200)
    model_version = StringField(null=True, default=None, max_length=120)
    artifact_sha256 = StringField(null=True, default=None, max_length=64)
    source_type = StringField(required=True, choices=EVENT_SOURCE_TYPES)
    camera_id = StringField(required=True, max_length=120)
    processed_at = DateTimeField(required=True)


class EmergencyEvent(Document):
    """A temporal decision record; it stores metadata, not continuous video."""

    event_id = StringField(required=True, unique=True, default=lambda: str(uuid4()))
    event_type = StringField(required=True, max_length=80)
    severity = StringField(required=True, choices=("info", "warning", "critical"))
    status = StringField(
        required=True,
        choices=("detected", "verified", "acknowledged", "resolved"),
        default="verified",
    )
    camera_id = StringField(required=True, max_length=120)
    track_id = StringField(default="", max_length=120)
    confidence = FloatField(min_value=0.0, max_value=1.0, default=0.0)
    duration_seconds = FloatField(min_value=0.0, default=0.0)
    frame_count = IntField(min_value=0, default=0)
    evidence_uri = StringField(default="", max_length=500)
    context = DictField(default=dict)
    provenance = EmbeddedDocumentField(EventProvenance, null=True, default=None)
    occurred_at = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "emergency_events",
        "indexes": ["-occurred_at", "camera_id", "status", "event_type"],
    }
