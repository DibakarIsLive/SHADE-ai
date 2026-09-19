"""Small immutable-ish data contracts shared by vision adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Frame:
    frame_number: int
    captured_at: datetime
    payload: Any = None
    width: int = 0
    height: int = 0


@dataclass(frozen=True)
class BoundingBox:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.left + self.right) / 2, (self.top + self.bottom) / 2)

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height else 0.0


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    bounding_box: BoundingBox


@dataclass(frozen=True)
class Track:
    track_id: str
    detection: Detection
    age_frames: int = 1


@dataclass(frozen=True)
class PoseSignal:
    posture: str
    verticality: float
    motion_score: float
    keypoints: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass(frozen=True)
class ActivityObservation:
    track_id: str
    activity: str
    confidence: float
    pose: PoseSignal
    observed_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VerificationDecision:
    verified: bool
    event_type: str | None
    confidence: float
    reason: str
    observation_count: int
    duration_seconds: float
