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
    def frames(self) -> Iterable[Frame]: ...

    def close(self) -> None: ...


class PersonDetector(Protocol):
    def detect(self, frame: Frame) -> list[Detection]: ...


class PersonTracker(Protocol):
    def update(self, detections: list[Detection], frame: Frame) -> list[Track]: ...


class PoseEstimator(Protocol):
    def estimate(self, frame: Frame, track: Track) -> PoseSignal: ...


class ActivityClassifier(Protocol):
    def classify(self, track: Track, pose: PoseSignal, frame: Frame) -> ActivityObservation: ...


class TemporalVerifier(Protocol):
    def observe(self, observation: ActivityObservation) -> object: ...
