from __future__ import annotations

import subprocess
import sys
import time

import pytest

from monitoring.supervisor import (
    MonitoringWorkerSupervisor,
    WorkerConflictError,
    WorkerStoppingError,
)


_EVENT_HELPERS = r'''
import json

def event(name, **payload):
    print("SHADE_WORKER_EVENT " + json.dumps({"event": name, **payload}), flush=True)
'''


@pytest.fixture
def supervisor_factory():
    processes = []

    def create(script, **overrides):
        def spawn(_command, **kwargs):
            process = subprocess.Popen(
                [sys.executable, "-u", "-c", script],
                **kwargs,
            )
            processes.append(process)
            return process

        supervisor = MonitoringWorkerSupervisor(
            process_factory=spawn,
            stop_grace_seconds=overrides.pop("stop_grace_seconds", 0.5),
            force_kill_wait_seconds=overrides.pop("force_kill_wait_seconds", 0.5),
            watch_poll_seconds=overrides.pop("watch_poll_seconds", 0.01),
            startup_timeout_seconds=overrides.pop("startup_timeout_seconds", 1.0),
            register_atexit=False,
            **overrides,
        )
        return supervisor

    yield create

    for process in processes:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=1)


def wait_for_status(supervisor, expected, timeout=2.0, *, cleanup_pending=None):
    deadline = time.monotonic() + timeout
    snapshot = supervisor.snapshot()
    while time.monotonic() < deadline:
        if snapshot["status"] == expected and (
            cleanup_pending is None or snapshot["cleanup_pending"] is cleanup_pending
        ):
            return snapshot
        time.sleep(0.01)
        snapshot = supervisor.snapshot()
    pytest.fail(f"expected {expected} with cleanup_pending={cleanup_pending}, got {snapshot}")


def ready_child(loop=True):
    tail = "while True: time.sleep(0.02)" if loop else "raise SystemExit(23)"
    signal_setup = (
        "signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))\n"
        if loop
        else ""
    )
    return (
        "import signal, sys, time\n"
        + _EVENT_HELPERS
        + "\n"
        + signal_setup
        + "event('provider_ready', provider='test-provider', model_name='test-model', inference_available=True)\n"
        + "event('source_ready')\n"
        + tail
    )


def test_supervisor_observes_ready_duplicate_start_stop_and_cleanup(supervisor_factory):
    supervisor = supervisor_factory(ready_child())

    initial, launched = supervisor.start("camera-01")
    assert launched is True
    assert initial["status"] == "STARTING"
    assert initial["worker_id"]

    running = wait_for_status(supervisor, "RUNNING")
    assert running["provider_ready"] is True
    assert running["source_ready"] is True
    assert running["provider"] == "test-provider"
    assert running["model_name"] == "test-model"
    assert running["ready_at"] is not None
    assert "pid" not in running

    duplicate, launched = supervisor.start("camera-01")
    assert launched is False
    assert duplicate["status"] == "RUNNING"
    assert duplicate["worker_id"] == running["worker_id"]
    with pytest.raises(WorkerConflictError):
        supervisor.start("camera-02")

    stopping = supervisor.stop()
    assert stopping["status"] == "STOPPING"
    assert stopping["stop_requested"] is True
    assert wait_for_status(supervisor, "STOPPED")["cleanup_pending"] is False
    assert supervisor.stop()["status"] == "STOPPED"
    supervisor.shutdown()


def test_supervisor_preserves_reported_camera_failure(supervisor_factory):
    script = (
        "import sys\n"
        + _EVENT_HELPERS
        + "\nevent('failed', code='CAMERA_UNAVAILABLE')\n"
        + "raise SystemExit(1)\n"
    )
    supervisor = supervisor_factory(script)

    initial, launched = supervisor.start("camera-01")
    assert launched is True
    assert initial["status"] == "STARTING"

    failed = wait_for_status(supervisor, "FAILED", cleanup_pending=False)
    assert failed["failure_code"] == "CAMERA_UNAVAILABLE"
    assert "video source" in failed["failure_reason"]
    supervisor.shutdown()


def test_supervisor_detects_unexpected_worker_exit(supervisor_factory):
    supervisor = supervisor_factory(ready_child(loop=False))

    supervisor.start("camera-01")
    failed = wait_for_status(supervisor, "FAILED")

    assert failed["failure_code"] == "WORKER_FAILED"
    assert failed["failure_reason"]
    assert failed["cleanup_pending"] is False
    supervisor.shutdown()


def test_supervisor_keeps_runtime_worker_crash_failed_when_stop_races_exit(supervisor_factory):
    script = (
        """import signal, sys, time
"""
        + _EVENT_HELPERS
        + """signal.signal(signal.SIGTERM, lambda *_: sys.exit(23))
event('provider_ready', provider='test-provider', model_name='test-model', inference_available=True)
event('source_ready')
while True: time.sleep(0.02)
"""
    )
    supervisor = supervisor_factory(script, stop_grace_seconds=0.5)

    supervisor.start("camera-01")
    wait_for_status(supervisor, "RUNNING")
    assert supervisor.stop()["status"] == "STOPPING"

    failed = wait_for_status(supervisor, "FAILED", cleanup_pending=False)
    assert failed["failure_code"] == "WORKER_FAILED"
    assert failed["cleanup_pending"] is False
    supervisor.shutdown()


def test_supervisor_times_out_worker_that_never_reports_readiness(supervisor_factory):
    supervisor = supervisor_factory(
        "import time\ntime.sleep(5)\n",
        startup_timeout_seconds=0.08,
        stop_grace_seconds=0.1,
    )

    supervisor.start("camera-01")
    failed = wait_for_status(
        supervisor, "FAILED", timeout=1.5, cleanup_pending=False
    )

    assert failed["failure_code"] == "STARTUP_TIMEOUT"
    assert failed["cleanup_pending"] is False
    supervisor.shutdown()


def test_supervisor_reports_spawn_failure_without_claiming_start(supervisor_factory):
    def fail_to_spawn(_command, **_kwargs):
        raise OSError("process creation failed")

    supervisor = MonitoringWorkerSupervisor(
        process_factory=fail_to_spawn,
        register_atexit=False,
    )

    snapshot, launched = supervisor.start("camera-01")

    assert launched is False
    assert snapshot["status"] == "FAILED"
    assert snapshot["failure_code"] == "WORKER_START_FAILED"
    assert snapshot["cleanup_pending"] is False
    supervisor.shutdown()


def test_supervisor_rejects_new_worker_while_existing_worker_is_stopping(supervisor_factory):
    supervisor = supervisor_factory(
        "import signal, time\n"
        + _EVENT_HELPERS
        + "\nsignal.signal(signal.SIGTERM, lambda *_: None)\n"
        + "event('provider_ready', provider='test-provider', model_name='test-model', inference_available=True)\n"
        + "event('source_ready')\n"
        + "while True: time.sleep(0.02)\n",
        stop_grace_seconds=0.5,
    )

    supervisor.start("camera-01")
    wait_for_status(supervisor, "RUNNING")
    assert supervisor.stop()["status"] == "STOPPING"

    with pytest.raises(WorkerStoppingError):
        supervisor.start("camera-02")

    stopped_or_failed = wait_for_status(
        supervisor, "FAILED", timeout=2.0, cleanup_pending=False
    )
    assert stopped_or_failed["failure_code"] == "SHUTDOWN_TIMEOUT"
    assert stopped_or_failed["cleanup_pending"] is False
    supervisor.shutdown()
