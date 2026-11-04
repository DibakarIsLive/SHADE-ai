"""Single-camera, in-memory supervisor for the existing standalone worker process."""

from __future__ import annotations

import atexit
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from django.conf import settings

from monitoring.protocol import LIFECYCLE_PREFIX


LOGGER = logging.getLogger(__name__)
STOP_GRACE_SECONDS = 4.0
FORCE_KILL_WAIT_SECONDS = 1.0
WATCH_POLL_SECONDS = 0.05
STARTUP_TIMEOUT_SECONDS = 60.0
ACTIVE_STATES = {"STARTING", "RUNNING", "STOPPING"}
_FAILURE_REASONS = {
    "CAMERA_UNAVAILABLE": "The configured video source could not be opened. Check that the saved video file exists and is readable.",
    "INFERENCE_UNAVAILABLE": "The configured inference provider or model could not be initialized.",
    "WORKER_FAILED": "The monitoring worker exited unexpectedly. Check the backend logs for details.",
    "WORKER_START_FAILED": "The monitoring worker process could not be started.",
    "STARTUP_TIMEOUT": "The worker did not report provider and video-source readiness before the startup timeout.",
    "SHUTDOWN_TIMEOUT": "The worker did not stop within the graceful shutdown period and required forceful cleanup.",
}


class WorkerConflictError(RuntimeError):
    """A different camera already owns the single supervised worker slot."""


class WorkerStoppingError(RuntimeError):
    """A new worker cannot start while the previous worker is stopping or being reaped."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class MonitoringWorkerSupervisor:
    """Own exactly one worker subprocess and report only observed lifecycle state."""

    def __init__(
        self,
        *,
        process_factory: Callable[..., Any] = subprocess.Popen,
        stop_grace_seconds: float = STOP_GRACE_SECONDS,
        force_kill_wait_seconds: float = FORCE_KILL_WAIT_SECONDS,
        watch_poll_seconds: float = WATCH_POLL_SECONDS,
        startup_timeout_seconds: float = STARTUP_TIMEOUT_SECONDS,
        register_atexit: bool = False,
    ) -> None:
        self._process_factory = process_factory
        self._stop_grace_seconds = stop_grace_seconds
        self._force_kill_wait_seconds = force_kill_wait_seconds
        self._watch_poll_seconds = watch_poll_seconds
        self._startup_timeout_seconds = startup_timeout_seconds
        self._lock = threading.RLock()
        self._process: Any | None = None
        self._reader_thread: threading.Thread | None = None
        self._watcher_thread: threading.Thread | None = None
        self._startup_deadline: float | None = None
        self._stop_deadline: float | None = None
        self._forced_kill = False
        self._closed = False
        self._state: dict[str, Any] = self._initial_state()
        if register_atexit:
            atexit.register(self.shutdown)

    @staticmethod
    def _initial_state() -> dict[str, Any]:
        return {
            "status": "STOPPED",
            "monitoring_intent": False,
            "camera_id": None,
            "worker_id": None,
            "started_at": None,
            "ready_at": None,
            "updated_at": _now(),
            "provider": None,
            "model_name": None,
            "provider_ready": False,
            "inference_available": None,
            "source_ready": False,
            "stop_requested": False,
            "failure_code": None,
            "failure_reason": None,
        }

    def _snapshot_locked(self) -> dict[str, Any]:
        """Add safe cleanup status without exposing the child process or its PID."""
        snapshot = dict(self._state)
        snapshot["cleanup_pending"] = (
            self._process is not None and snapshot["status"] in {"STOPPING", "FAILED"}
        )
        return snapshot

    def snapshot(self) -> dict[str, Any]:
        """Return the safe public state; never expose a PID or process handle."""
        with self._lock:
            return self._snapshot_locked()

    def start(self, camera_id: str) -> tuple[dict[str, Any], bool]:
        """Spawn the shared `run_monitor` command without waiting for initialization."""
        if not isinstance(camera_id, str) or not camera_id.strip():
            raise ValueError("camera_id must be a non-empty string")

        with self._lock:
            current_status = self._state["status"]
            if current_status == "STOPPING":
                raise WorkerStoppingError("The existing monitoring worker is still stopping.")
            if current_status in {"STARTING", "RUNNING"}:
                if self._state["camera_id"] == camera_id:
                    return self._snapshot_locked(), False
                raise WorkerConflictError("A different camera already has an active monitoring worker.")
            if self._process is not None:
                raise WorkerStoppingError("The previous worker is still being cleaned up.")
            if self._closed:
                raise RuntimeError("The monitoring worker supervisor is shutting down.")

            worker_id = str(uuid4())
            now = _now()
            self._state = {
                **self._initial_state(),
                "status": "STARTING",
                "monitoring_intent": True,
                "camera_id": camera_id,
                "worker_id": worker_id,
                "started_at": now,
                "updated_at": now,
            }
            self._startup_deadline = time.monotonic() + self._startup_timeout_seconds
            self._stop_deadline = None
            self._forced_kill = False

            command = [
                sys.executable,
                "manage.py",
                "run_monitor",
                "--camera-id",
                camera_id,
                "--supervised",
            ]
            try:
                process = self._process_factory(
                    command,
                    cwd=str(settings.BASE_DIR),
                    env=os.environ.copy(),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    start_new_session=(os.name == "posix"),
                )
            except Exception:
                LOGGER.exception("monitor.supervisor_spawn_failure camera_id=%s", camera_id)
                self._fail_locked("WORKER_START_FAILED")
                self._startup_deadline = None
                return self._snapshot_locked(), False

            self._process = process
            self._reader_thread = threading.Thread(
                target=self._consume_output,
                args=(worker_id, process),
                name=f"shade-worker-output-{worker_id[:8]}",
                daemon=True,
            )
            self._watcher_thread = threading.Thread(
                target=self._watch_process,
                args=(worker_id, process),
                name=f"shade-worker-watch-{worker_id[:8]}",
                daemon=True,
            )
            try:
                self._reader_thread.start()
                self._watcher_thread.start()
            except Exception:
                LOGGER.exception("monitor.supervisor_thread_start_failure worker_id=%s", worker_id)
                self._reap_after_thread_start_failure(process, self._reader_thread)
                self._process = None
                self._fail_locked("WORKER_START_FAILED")
                self._startup_deadline = None
                return self._snapshot_locked(), False

            return self._snapshot_locked(), True

    def stop(self) -> dict[str, Any]:
        """Request shutdown and report STOPPING until process exit is observed."""
        process: Any | None = None
        should_terminate = False
        with self._lock:
            if self._state["status"] in {"STARTING", "RUNNING"}:
                self._state["status"] = "STOPPING"
                self._state["monitoring_intent"] = False
                self._state["stop_requested"] = True
                self._state["updated_at"] = _now()
                self._stop_deadline = time.monotonic() + self._stop_grace_seconds
                process = self._process
                should_terminate = process is not None
            snapshot = self._snapshot_locked()

        if should_terminate:
            self._terminate(process, "monitor.supervisor_terminate_failure")
        return snapshot

    def shutdown(self) -> None:
        """Stop and reap the child on application shutdown; escalate after a bound."""
        with self._lock:
            self._closed = True
            process = self._process
            watcher = self._watcher_thread
            reader = self._reader_thread
            active = self._state["status"] in ACTIVE_STATES
        if process is None:
            return

        if active:
            self.stop()
        join_timeout = self._stop_grace_seconds + self._force_kill_wait_seconds + 1.0
        if watcher is not None:
            watcher.join(timeout=join_timeout)

        # The watcher normally performs this escalation. Keep shutdown bounded even
        # if its thread itself failed, then wait for the direct child to be reaped.
        try:
            return_code = process.poll()
        except Exception:
            return_code = None
        if return_code is None:
            try:
                process.kill()
            except (OSError, ProcessLookupError):
                pass
            try:
                process.wait(timeout=self._force_kill_wait_seconds)
            except (subprocess.TimeoutExpired, OSError, ChildProcessError):
                LOGGER.error("monitor.supervisor_shutdown_reap_timeout worker_id=%s", self.snapshot()["worker_id"])
        if reader is not None:
            reader.join(timeout=self._force_kill_wait_seconds)
        if watcher is not None:
            watcher.join(timeout=self._force_kill_wait_seconds)

    def _consume_output(self, worker_id: str, process: Any) -> None:
        stream = getattr(process, "stdout", None)
        if stream is None:
            return
        try:
            for line in stream:
                if not line.startswith(LIFECYCLE_PREFIX):
                    continue
                try:
                    message = json.loads(line[len(LIFECYCLE_PREFIX) :])
                except (json.JSONDecodeError, TypeError):
                    LOGGER.warning("monitor.supervisor_invalid_worker_event worker_id=%s", worker_id)
                    continue
                if isinstance(message, dict):
                    self._apply_event(worker_id, process, message)
        except (OSError, ValueError):
            LOGGER.exception("monitor.supervisor_output_read_failure worker_id=%s", worker_id)

    def _apply_event(self, worker_id: str, process: Any, message: dict[str, Any]) -> None:
        event = message.get("event")
        terminate_after_event = False
        with self._lock:
            if self._state["worker_id"] != worker_id or self._state["status"] not in {"STARTING", "RUNNING"}:
                return
            if event == "provider_ready":
                provider = message.get("provider")
                model_name = message.get("model_name")
                available = message.get("inference_available")
                self._state["provider"] = provider[:120] if isinstance(provider, str) else None
                self._state["model_name"] = model_name[:200] if isinstance(model_name, str) else None
                self._state["provider_ready"] = True
                self._state["inference_available"] = available if isinstance(available, bool) else None
                self._state["updated_at"] = _now()
                # Provider construction succeeded before provider_ready is emitted.
                # The explicit development-null provider initializes successfully but
                # intentionally cannot perform inference; expose that capability fact
                # without misreporting its process/source lifecycle as a failure.
            elif event == "source_ready":
                if not self._state["provider_ready"]:
                    self._fail_locked("INFERENCE_UNAVAILABLE")
                    terminate_after_event = True
                else:
                    self._state["source_ready"] = True
                    self._state["status"] = "RUNNING"
                    self._state["ready_at"] = _now()
                    self._state["updated_at"] = self._state["ready_at"]
            elif event == "failed":
                code = message.get("code")
                self._fail_locked(code if isinstance(code, str) and code in _FAILURE_REASONS else "WORKER_FAILED")
                terminate_after_event = True
            if terminate_after_event:
                self._stop_deadline = time.monotonic() + self._stop_grace_seconds

        if terminate_after_event:
            self._terminate(process, "monitor.supervisor_failed_worker_terminate_error")

    def _watch_process(self, worker_id: str, process: Any) -> None:
        while True:
            action: str | None = None
            with self._lock:
                if self._state["worker_id"] != worker_id:
                    return
                now = time.monotonic()
                state = self._state["status"]
                if state == "STARTING" and self._startup_deadline is not None and now >= self._startup_deadline:
                    self._fail_locked("STARTUP_TIMEOUT")
                    self._stop_deadline = now + self._stop_grace_seconds
                    self._startup_deadline = None
                    action = "terminate"
                elif state == "STOPPING" and self._stop_deadline is not None and now >= self._stop_deadline:
                    self._fail_locked("SHUTDOWN_TIMEOUT")
                    self._stop_deadline = None
                    self._forced_kill = True
                    action = "kill"
                elif state == "FAILED" and self._stop_deadline is not None and now >= self._stop_deadline:
                    self._stop_deadline = None
                    self._forced_kill = True
                    action = "kill"

            if action == "terminate":
                self._terminate(process, "monitor.supervisor_startup_timeout_terminate_error")
            elif action == "kill":
                LOGGER.warning("monitor.supervisor_force_kill worker_id=%s", worker_id)
                try:
                    process.kill()
                except (OSError, ProcessLookupError):
                    pass

            try:
                return_code = process.wait(timeout=self._watch_poll_seconds)
            except subprocess.TimeoutExpired:
                continue
            except (OSError, ChildProcessError):
                LOGGER.exception("monitor.supervisor_process_wait_failure worker_id=%s", worker_id)
                return_code = -1

            reader = self._reader_thread
            if reader is not None and reader is not threading.current_thread():
                reader.join()

            with self._lock:
                if self._state["worker_id"] != worker_id:
                    return
                if self._state["status"] != "FAILED":
                    if self._forced_kill:
                        self._fail_locked("SHUTDOWN_TIMEOUT")
                    elif self._state["stop_requested"] and return_code != 0:
                        self._fail_locked("WORKER_FAILED")
                    elif self._state["stop_requested"]:
                        self._state["status"] = "STOPPED"
                        self._state["monitoring_intent"] = False
                        self._state["updated_at"] = _now()
                    elif return_code == 0:
                        # A finite file ending normally is a completed, stopped worker.
                        self._state["status"] = "STOPPED"
                        self._state["monitoring_intent"] = False
                        self._state["updated_at"] = _now()
                    else:
                        self._fail_locked("WORKER_FAILED")
                self._process = None
                self._startup_deadline = None
                self._stop_deadline = None
            return

    def _fail_locked(self, code: str) -> None:
        self._state["status"] = "FAILED"
        self._state["monitoring_intent"] = False
        self._state["failure_code"] = code
        self._state["failure_reason"] = _FAILURE_REASONS[code]
        self._state["updated_at"] = _now()

    def _terminate(self, process: Any, log_message: str) -> None:
        try:
            process.terminate()
        except (OSError, ProcessLookupError):
            # The watcher will settle state from the actual process exit status.
            pass
        except Exception:
            LOGGER.exception(log_message)

    def _reap_after_thread_start_failure(self, process: Any, reader: threading.Thread) -> None:
        self._terminate(process, "monitor.supervisor_thread_failure_terminate_error")
        try:
            process.wait(timeout=self._stop_grace_seconds)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except (OSError, ProcessLookupError):
                pass
            try:
                process.wait(timeout=self._force_kill_wait_seconds)
            except (subprocess.TimeoutExpired, OSError, ChildProcessError):
                LOGGER.exception("monitor.supervisor_thread_failure_reap_timeout")
        except (OSError, ChildProcessError):
            LOGGER.exception("monitor.supervisor_thread_failure_wait_error")
        if reader.ident is not None and reader is not threading.current_thread():
            reader.join(timeout=self._force_kill_wait_seconds)


worker_supervisor = MonitoringWorkerSupervisor(register_atexit=True)
