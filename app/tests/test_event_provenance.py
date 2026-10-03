from __future__ import annotations

from datetime import datetime, timezone

import pytest

from events.documents import EmergencyEvent, EventProvenance
from events.provenance import (
    EventProvenanceValidationError,
    build_event_provenance,
)
from events import services


PROCESSED_AT = datetime(2026, 1, 1, 12, 30, tzinfo=timezone.utc)
BASE_PROVENANCE = {
    "provider": "  rtmo-s  ",
    "model_identifier": " rtmo-s-body7 ",
    "model_version": None,
    "artifact_sha256": "A" * 64,
    "source_type": "video_file",
    "camera_id": " camera-01 ",
    "processed_at": PROCESSED_AT,
}


def test_provenance_is_normalized_without_confusing_artifact_digest_and_version():
    provenance = build_event_provenance(BASE_PROVENANCE, event_camera_id="camera-01")

    assert isinstance(provenance, EventProvenance)
    assert provenance.provider == "rtmo-s"
    assert provenance.model_identifier == "rtmo-s-body7"
    assert provenance.model_version is None
    assert provenance.artifact_sha256 == "a" * 64
    assert provenance.source_type == "video_file"
    assert provenance.camera_id == "camera-01"
    assert provenance.processed_at == PROCESSED_AT


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"provider": " "}, "provider"),
        ({"artifact_sha256": "not-a-digest"}, "64-character hexadecimal"),
        ({"source_type": "unknown"}, "source_type"),
        ({"camera_id": "other-camera"}, "must match"),
        ({"camera_id": " "}, "camera_id"),
        ({"processed_at": datetime(2026, 1, 1)}, "timezone-aware"),
        ({"model_version": " "}, "model_version"),
        ({"unexpected": "value"}, "unsupported fields"),
    ],
)
def test_provenance_validator_rejects_invalid_values(changes, message):
    payload = {**BASE_PROVENANCE, **changes}

    with pytest.raises(EventProvenanceValidationError, match=message):
        build_event_provenance(payload, event_camera_id="camera-01")


def test_legacy_event_without_provenance_remains_valid():
    event = EmergencyEvent(
        event_id="legacy-event",
        event_type="fall",
        severity="critical",
        status="verified",
        camera_id="camera-01",
    )

    assert event.provenance is None
    serialized = services.serialize_event(event)
    assert serialized["provenance"] is None
    assert serialized["event_id"] == "legacy-event"
    assert serialized["context"] == {}


def test_create_event_validates_provenance_before_connecting_to_database(monkeypatch):
    connected = False

    def mark_connected():
        nonlocal connected
        connected = True

    monkeypatch.setattr(services, "connect_mongodb", mark_connected)

    with pytest.raises(EventProvenanceValidationError, match="unsupported fields"):
        services.create_event(
            {
                "event_type": "fall",
                "severity": "critical",
                "camera_id": "camera-01",
                "provenance": {**BASE_PROVENANCE, "private_path": "/private/model.onnx"},
            }
        )

    assert connected is False


def test_create_event_persists_and_serializes_typed_provenance(monkeypatch):
    saved = []

    class FakeEvent:
        def __init__(self, **data):
            self.__dict__.update(
                {
                    "status": "verified",
                    "track_id": "",
                    "confidence": 0.0,
                    "duration_seconds": 0.0,
                    "frame_count": 0,
                    "evidence_uri": "",
                    "context": {},
                    **data,
                }
            )
            self.event_id = "persisted-event"
            self.provenance = self.__dict__.get("provenance")
            self.occurred_at = PROCESSED_AT
            self.created_at = PROCESSED_AT

        def save(self):
            saved.append(self)
            return self

    monkeypatch.setattr(services, "connect_mongodb", lambda: None)
    monkeypatch.setattr(services, "EmergencyEvent", FakeEvent)

    result = services.create_event(
        {
            "event_type": "fall",
            "severity": "critical",
            "status": "verified",
            "camera_id": "camera-01",
            "confidence": 0.9,
            "provenance": BASE_PROVENANCE,
        }
    )

    assert len(saved) == 1
    assert isinstance(saved[0].provenance, EventProvenance)
    assert result["provenance"] == {
        "provider": "rtmo-s",
        "model_identifier": "rtmo-s-body7",
        "model_version": None,
        "artifact_sha256": "a" * 64,
        "source_type": "video_file",
        "camera_id": "camera-01",
        "processed_at": "2026-01-01T12:30:00Z",
    }
    assert not any("path" in key for key in result["provenance"])


def test_create_event_keeps_missing_provenance_null_for_legacy_callers(monkeypatch):
    saved = []

    class FakeEvent:
        def __init__(self, **data):
            self.__dict__.update(
                {
                    "status": "verified",
                    "track_id": "",
                    "confidence": 0.0,
                    "duration_seconds": 0.0,
                    "frame_count": 0,
                    "evidence_uri": "",
                    "context": {},
                    **data,
                }
            )
            self.event_id = "legacy-event"
            self.provenance = self.__dict__.get("provenance")
            self.occurred_at = PROCESSED_AT
            self.created_at = PROCESSED_AT

        def save(self):
            saved.append(self)

    monkeypatch.setattr(services, "connect_mongodb", lambda: None)
    monkeypatch.setattr(services, "EmergencyEvent", FakeEvent)

    result = services.create_event(
        {"event_type": "fall", "severity": "critical", "camera_id": "camera-01"}
    )

    assert len(saved) == 1
    assert saved[0].provenance is None
    assert result["provenance"] is None
