"""Protocols that keep model vendors replaceable."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from vision.types import (
    ActivityObservation,
    Detection,
    Frame,
    PoseSignal,
    Track,
)


class CameraSource(Protocol):
    """A source with an explicit lifecycle and optional frame metadata."""

    @property
    def is_opened(self) -> bool: ...

    @property
    def width(self) -> int | None: ...

    @property
    def height(self) -> int | None: ...

    @property
    def fps(self) -> float | None: ...

    def open(self) -> None: ...

    def frames(self) -> Iterable[Frame]: ...

    def close(self) -> None: ...


class PersonDetector(Protocol):
    def detect(self, frame: Frame) -> list[Detection]: ...


class PersonTracker(Protocol):
    @property
    def retained_track_ids(self) -> frozenset[str]: ...

    def update(self, detections: list[Detection], frame: Frame) -> list[Track]: ...


class PoseEstimator(Protocol):
    def estimate(self, frame: Frame, track: Track) -> PoseSignal: ...


class ActivityClassifier(Protocol):
    def classify(self, track: Track, pose: PoseSignal, frame: Frame) -> ActivityObservation: ...


class TemporalVerifier(Protocol):
    def observe(self, observation: ActivityObservation) -> object: ...

    def retain_track_ids(self, track_ids: frozenset[str]) -> None: ...
