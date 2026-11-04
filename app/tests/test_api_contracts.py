from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from rest_framework.test import APIClient

from cameras import views as camera_views
from events import views as event_views
from monitoring import views as monitoring_views


@pytest.fixture
def enabled_video_camera():
    return SimpleNamespace(
        camera_id="camera-01",
        enabled=True,
        source_type="video_file",
        source_uri="/tmp/authorized-control-video.avi",
    )


def worker_snapshot(status="STOPPED", **overrides):
    return {
        "status": status,
        "monitoring_intent": status in {"STARTING", "RUNNING"},
        "camera_id": "camera-01" if status != "STOPPED" else None,
        "worker_id": "worker-123" if status != "STOPPED" else None,
        "started_at": "2026-10-03T10:00:00Z" if status != "STOPPED" else None,
        "ready_at": "2026-10-03T10:00:01Z" if status == "RUNNING" else None,
        "updated_at": "2026-10-03T10:00:01Z",
        "provider": "rtmo-s",
        "model_name": "RTMO-S",
        "provider_ready": status == "RUNNING",
        "inference_available": True,
        "source_ready": status == "RUNNING",
        "stop_requested": status == "STOPPING",
        "failure_code": None,
        "failure_reason": None,
        "cleanup_pending": False,
        **overrides,
    }


@pytest.fixture
def client():
    return APIClient()


def test_api_root_exposes_service_links(client):
    response = client.get("/api/")

    assert response.status_code == 200
    assert response.data["name"] == "SHADE-ai"
    assert response.data["links"]["health"] == "/api/health/"
    assert response.data["links"]["monitoring_socket"] == "/ws/monitoring/"


def test_capabilities_expose_implemented_and_planned_boundaries(client):
    response = client.get("/api/capabilities/")

    assert response.status_code == 200
    assert "temporal_fall_verification" in response.data["implemented"]
    assert "rtmo_s_onnx_cpu_observation_adapter" in response.data["experimental"]
    assert "geometric_posture_heuristics_not_activity_model" in response.data["experimental"]
    assert "representative_fall_evaluation" in response.data["planned"]
    assert "falling" in response.data["activity_categories"]


def test_health_returns_safe_degraded_report_when_mongodb_is_unavailable(client, monkeypatch):
    monkeypatch.setattr(
        "core.views.check_mongodb",
        lambda: {"available": False, "status": "unavailable", "database": "shade_ai"},
    )

    response = client.get("/api/health/")

    assert response.status_code == 200
    assert response.data["status"] == "degraded"
    assert response.data["database"]["available"] is False
    assert response.data["safety"]["human_review_required"] is True


def test_camera_list_falls_back_to_explicit_persistence_state(client, monkeypatch):
    def unavailable():
        raise RuntimeError("MongoDB unavailable")

    monkeypatch.setattr(camera_views, "list_cameras", unavailable)

    response = client.get("/api/cameras/")

    assert response.status_code == 200
    assert response.data["items"] == []
    assert response.data["persistence"] == "unavailable"


def test_camera_create_validates_source_uri_before_persistence(client, monkeypatch):
    create_called = False

    def should_not_run(data):  # noqa: ARG001
        nonlocal create_called
        create_called = True
        return {}

    monkeypatch.setattr(camera_views, "create_camera", should_not_run)
    response = client.post(
        "/api/cameras/",
        {"name": "Hallway", "source_type": "rtsp"},
        format="json",
    )

    assert response.status_code == 400
    assert "source_uri" in response.data
    assert create_called is False


def test_event_create_returns_created_contract(client, monkeypatch):
    payload = {
        "event_id": "event-001",
        "event_type": "Fall verification",
        "severity": "critical",
        "status": "verified",
        "camera_id": "camera-01",
        "track_id": "person-01",
        "confidence": 0.91,
        "duration_seconds": 1.2,
        "frame_count": 12,
        "context": {"activity": "lying"},
        "provenance": {
            "provider": "rtmo-s",
            "model_identifier": "rtmo-s-body7",
            "model_version": None,
            "artifact_sha256": "a" * 64,
            "source_type": "video_file",
            "camera_id": "camera-01",
            "processed_at": "2026-01-01T00:00:00Z",
        },
    }
    monkeypatch.setattr(event_views, "create_event", lambda data: {**payload, **data})

    response = client.post("/api/events/", payload, format="json")

    assert response.status_code == 201
    assert response.data["event_type"] == "Fall verification"
    assert response.data["confidence"] == 0.91
    assert response.data["provenance"]["provider"] == "rtmo-s"
    assert response.data["provenance"]["model_version"] is None
    assert response.data["provenance"]["artifact_sha256"] == "a" * 64
    assert response.data["provenance"]["processed_at"] == datetime(
        2026, 1, 1, tzinfo=timezone.utc
    )


def test_event_create_rejects_unknown_nested_provenance_fields(client, monkeypatch):
    create_called = False

    def should_not_run(_data):
        nonlocal create_called
        create_called = True
        return {}

    monkeypatch.setattr(event_views, "create_event", should_not_run)
    response = client.post(
        "/api/events/",
        {
            "event_type": "fall",
            "severity": "critical",
            "camera_id": "camera-01",
            "provenance": {
                "provider": "rtmo-s",
                "source_type": "video_file",
                "camera_id": "camera-01",
                "processed_at": "2026-01-01T00:00:00Z",
                "artifact_path": "/private/model.onnx",
            },
        },
        format="json",
    )

    assert response.status_code == 400
    assert "provenance" in response.data
    assert create_called is False


def test_event_create_rejects_mismatched_provenance_camera(client, monkeypatch):
    create_called = False

    def should_not_run(_data):
        nonlocal create_called
        create_called = True
        return {}

    monkeypatch.setattr(event_views, "create_event", should_not_run)
    response = client.post(
        "/api/events/",
        {
            "event_type": "fall",
            "severity": "critical",
            "camera_id": "camera-01",
            "provenance": {
                "provider": "rtmo-s",
                "source_type": "video_file",
                "camera_id": "camera-02",
                "processed_at": "2026-01-01T00:00:00Z",
            },
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["provenance"]["camera_id"] == "Must match the event camera_id."
    assert create_called is False


def test_monitoring_api_reports_observed_start_and_stop_transitions(
    client, enabled_video_camera, monkeypatch
):
    current = worker_snapshot("STOPPED")
    starts = []

    def start(camera_id):
        nonlocal current
        starts.append(camera_id)
        current = worker_snapshot("STARTING")
        return current, True

    def stop():
        nonlocal current
        current = worker_snapshot("STOPPING", stop_requested=True, cleanup_pending=True)
        return current

    monkeypatch.setattr(monitoring_views, "get_camera", lambda _camera_id: enabled_video_camera)
    monkeypatch.setattr(monitoring_views.worker_supervisor, "start", start)
    monkeypatch.setattr(monitoring_views.worker_supervisor, "snapshot", lambda: current)
    monkeypatch.setattr(monitoring_views.worker_supervisor, "stop", stop)

    start_response = client.post(
        "/api/monitoring/start/", {"camera_id": "camera-01"}, format="json"
    )
    assert start_response.status_code == 202
    assert start_response.data["status"] == "STARTING"
    assert start_response.data["camera_id"] == "camera-01"
    assert start_response.data["monitoring_intent"] is True
    assert starts == ["camera-01"]

    current = worker_snapshot("RUNNING")
    status_response = client.get("/api/monitoring/status/")
    assert status_response.status_code == 200
    assert status_response.data["status"] == "RUNNING"
    assert status_response.data["source_ready"] is True
    assert status_response["Cache-Control"] == "no-store"

    stop_response = client.post("/api/monitoring/stop/", {}, format="json")
    assert stop_response.status_code == 202
    assert stop_response.data["status"] == "STOPPING"
    assert stop_response.data["stop_requested"] is True

    current = worker_snapshot("STOPPED")
    stopped_response = client.get("/api/monitoring/status/")
    assert stopped_response.data["status"] == "STOPPED"


def test_monitoring_start_is_idempotent_for_the_same_camera(
    client, enabled_video_camera, monkeypatch
):
    monkeypatch.setattr(monitoring_views, "get_camera", lambda _camera_id: enabled_video_camera)
    monkeypatch.setattr(
        monitoring_views.worker_supervisor,
        "start",
        lambda _camera_id: (worker_snapshot("RUNNING"), False),
    )

    response = client.post(
        "/api/monitoring/start/", {"camera_id": "camera-01"}, format="json"
    )

    assert response.status_code == 200
    assert response.data["status"] == "RUNNING"


@pytest.mark.parametrize(
    ("camera", "expected_status", "detail"),
    [
        (None, 404, "not found"),
        (SimpleNamespace(camera_id="camera-01", enabled=False, source_type="video_file", source_uri="/tmp/a.avi"), 400, "disabled"),
        (SimpleNamespace(camera_id="camera-01", enabled=True, source_type="webcam", source_uri="/dev/video0"), 400, "video_file"),
        (SimpleNamespace(camera_id="camera-01", enabled=True, source_type="video_file", source_uri=" "), 400, "URI is missing"),
    ],
)
def test_monitoring_start_rejects_invalid_camera_configuration(
    client, monkeypatch, camera, expected_status, detail
):
    start_called = False

    def should_not_start(_camera_id):
        nonlocal start_called
        start_called = True
        return worker_snapshot("STARTING"), True

    monkeypatch.setattr(monitoring_views, "get_camera", lambda _camera_id: camera)
    monkeypatch.setattr(monitoring_views.worker_supervisor, "start", should_not_start)

    response = client.post(
        "/api/monitoring/start/", {"camera_id": "camera-01"}, format="json"
    )

    assert response.status_code == expected_status
    assert detail.lower() in response.data["detail"].lower()
    assert start_called is False


def test_monitoring_stop_is_idempotent_for_a_stopped_worker(client, monkeypatch):
    monkeypatch.setattr(
        monitoring_views.worker_supervisor,
        "stop",
        lambda: worker_snapshot("STOPPED"),
    )

    response = client.post("/api/monitoring/stop/", {}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "STOPPED"


def test_monitoring_status_exposes_safe_worker_failure(client, monkeypatch):
    failure = worker_snapshot(
        "FAILED",
        monitoring_intent=False,
        failure_code="CAMERA_UNAVAILABLE",
        failure_reason="The configured video source could not be opened.",
    )
    monkeypatch.setattr(monitoring_views.worker_supervisor, "snapshot", lambda: failure)

    response = client.get("/api/monitoring/status/")

    assert response.status_code == 200
    assert response.data["status"] == "FAILED"
    assert response.data["failure_code"] == "CAMERA_UNAVAILABLE"
    assert "/Users/" not in response.data["failure_reason"]
