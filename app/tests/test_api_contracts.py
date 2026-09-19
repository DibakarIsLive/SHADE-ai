import pytest
from rest_framework.test import APIClient

from cameras import views as camera_views
from events import views as event_views
from monitoring.runtime import monitoring_controller


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
    assert "validated_detector_artifacts" in response.data["planned"]
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
    }
    monkeypatch.setattr(event_views, "create_event", lambda data: {**payload, **data})

    response = client.post("/api/events/", payload, format="json")

    assert response.status_code == 201
    assert response.data["event_type"] == "Fall verification"
    assert response.data["confidence"] == 0.91


def test_monitoring_start_and_stop_update_control_plane(client):
    monitoring_controller.stop()

    start_response = client.post("/api/monitoring/start/", {"camera_id": "camera-01"}, format="json")
    assert start_response.status_code == 202
    assert start_response.data["status"] == "armed"
    assert start_response.data["camera_id"] == "camera-01"
    assert start_response.data["session_id"].startswith("local-")

    status_response = client.get("/api/monitoring/status/")
    assert status_response.data["status"] == "armed"

    stop_response = client.post("/api/monitoring/stop/", {}, format="json")
    assert stop_response.status_code == 202
    assert stop_response.data["status"] == "idle"
    assert stop_response.data["session_id"] is None
