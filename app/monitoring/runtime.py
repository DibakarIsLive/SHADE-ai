"""Process-local monitoring intent used by the first local dashboard slice."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class MonitoringController:
    """Keep HTTP control state separate from future camera-processing workers."""

    status: str = "idle"
    camera_id: str | None = None
    session_id: str | None = None
    started_at: str | None = None
    updated_at: str = field(default_factory=_now)
    lock: Lock = field(default_factory=Lock, repr=False)

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "status": self.status,
                "camera_id": self.camera_id,
                "session_id": self.session_id,
                "started_at": self.started_at,
                "updated_at": self.updated_at,
            }

    def start(self, camera_id: str) -> dict:
        with self.lock:
            self.status = "armed"
            self.camera_id = camera_id
            self.session_id = f"local-{int(datetime.now(timezone.utc).timestamp())}"
            self.started_at = _now()
            self.updated_at = self.started_at
        return self.snapshot()

    def stop(self) -> dict:
        with self.lock:
            self.status = "idle"
            self.session_id = None
            self.started_at = None
            self.updated_at = _now()
        return self.snapshot()


monitoring_controller = MonitoringController()
