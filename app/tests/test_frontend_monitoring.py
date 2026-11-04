from pathlib import Path
import re


def read_web_source(path: str) -> str:
    return (Path(__file__).parents[2] / "web" / "src" / path).read_text(encoding="utf-8")


def test_frontend_normalizes_only_authoritative_worker_lifecycle_states():
    source = read_web_source("App.jsx")

    assert 'const WORKER_STATES = ["STOPPED", "STARTING", "RUNNING", "STOPPING", "FAILED"]' in source
    assert 'if (typeof monitoring.provider_ready !== "boolean" || typeof monitoring.source_ready !== "boolean") return null;' in source
    assert 'if (monitoring.status === "RUNNING" && (!monitoring.provider_ready || !monitoring.source_ready)) return null;' in source
    assert 'if (monitoring.status === "FAILED" && !monitoring.failure_code) return null;' in source
    assert 'monitoring.monitoring_intent' not in source


def test_frontend_polls_only_active_or_cleaning_workers_and_cleans_timer():
    source = read_web_source("App.jsx")

    assert "const MONITORING_POLL_INTERVAL_MS = 1000;" in source
    assert "if ((!ACTIVE_WORKER_STATES.includes(data.monitoring?.status) && !cleanupPending) || controlPending) return undefined;" in source
    assert "window.setTimeout(pollStatus, MONITORING_POLL_INTERVAL_MS)" in source
    assert "window.clearTimeout(timeoutId)" in source
    assert "if (!cancelled && requestId === monitoringSequence.current)" in source
    assert "let timeoutId;" in source


def test_frontend_control_response_supersedes_stale_dashboard_and_poll_responses():
    source = read_web_source("App.jsx")

    assert "setControlPending(true);\n    ++monitoringSequence.current;" in source
    assert "loadSequence.current += 1;\n      ++monitoringSequence.current;\n      setData((current) => ({ ...current, monitoring }));" in source
    assert 'const acceptedStates = stoppingWorker ? ["STOPPING", "STOPPED", "FAILED"] : ["STARTING", "RUNNING", "FAILED"];' in source
    assert "setControlPending(false);" in source


def test_camera_controls_expose_worker_states_not_process_local_intent():
    camera_grid = read_web_source("components/CameraGrid.jsx")
    topbar = read_web_source("components/Topbar.jsx")
    styles = read_web_source("styles.css")

    assert 'workerState = "STOPPED"' in camera_grid
    assert 'workerState === "RUNNING"' in camera_grid
    assert 'camera.source_type === "video_file"' in camera_grid
    assert "Worker slot in use" in camera_grid
    assert "Cancel startup" in camera_grid
    assert "workerState.toLowerCase()" in camera_grid
    assert "monitoringActive" not in camera_grid
    assert "monitoringArmed" not in camera_grid
    assert 'STOPPING: "Stopping…"' in topbar
    assert 'FAILED: "Failed"' in topbar
    assert "monitoring-pill--failed" in styles
    assert "feed-status--running" in styles
    assert "feed-status--failed" in styles


def test_camera_grid_has_no_undefined_monitoring_props():
    app = read_web_source("App.jsx")
    camera_props = re.findall(r"<CameraGrid\b([^>]*)/>", app)

    assert len(camera_props) == 2
    assert all("workerState={monitoringStatus}" in props for props in camera_props)
    assert all("monitoringActive=" not in props for props in camera_props)
