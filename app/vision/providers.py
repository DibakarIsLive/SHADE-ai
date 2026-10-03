"""Explicit inference-provider boundary and a non-detecting development provider."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from django.conf import settings

from vision.interfaces import ActivityClassifier, PersonDetector, PersonTracker, PoseEstimator
from vision.pipeline import VisionPipeline
from vision.temporal import FallTemporalVerifier
from vision.types import ActivityObservation, Detection, Frame, PoseSignal, Track

LOGGER = logging.getLogger(__name__)


class VisionProvider(Protocol):
    """Build the existing vendor-neutral pipeline and report inference readiness."""

    @property
    def name(self) -> str: ...

    @property
    def inference_available(self) -> bool: ...

    def build_pipeline(self) -> VisionPipeline: ...


class _NoDetections:
    def detect(self, frame: Frame) -> list[Detection]:  # noqa: ARG002
        return []


class _NoTracks:
    @property
    def retained_track_ids(self) -> frozenset[str]:
        return frozenset()

    def update(self, detections: list[Detection], frame: Frame) -> list[Track]:  # noqa: ARG002
        return []


class _UnavailablePoseEstimator:
    def estimate(self, frame: Frame, track: Track) -> PoseSignal:  # noqa: ARG002
        raise RuntimeError("Pose inference is unavailable in the development null provider.")


class _UnavailableActivityClassifier:
    def classify(
        self,
        track: Track,
        pose: PoseSignal,
        frame: Frame,
    ) -> ActivityObservation:  # noqa: ARG002
        raise RuntimeError("Activity inference is unavailable in the development null provider.")


class _RTMOCompatibleAdapter:
    """Bridge one model inference pass to detector, pose, and activity protocols."""

    def __init__(self, adapter) -> None:
        self.adapter = adapter

    def detect(self, frame: Frame) -> list[Detection]:
        return self.adapter.detect(frame)

    @property
    def retained_track_ids(self) -> frozenset[str]:
        return self.adapter.tracks.retained_track_ids

    def update(self, detections: list[Detection], frame: Frame) -> list[Track]:
        tracks = self.adapter.tracks.update(detections, frame)
        active_track_ids = {track.track_id for track in self.adapter.tracks.active_tracks}
        self.adapter._previous_centers = {
            track_id: center
            for track_id, center in self.adapter._previous_centers.items()
            if track_id in active_track_ids
        }
        return tracks

    def estimate(self, frame: Frame, track: Track) -> PoseSignal:
        return self.adapter.pose_for(frame, track)

    def classify(
        self,
        track: Track,
        pose: PoseSignal,
        frame: Frame,
    ) -> ActivityObservation:
        return self.adapter.classify(track, pose, frame)


class RTMOVisionProvider:
    """Explicit, fail-closed RTMO-S CPU provider; never downloads or falls back."""

    name = "mmpose-rtmo-s-body7-onnx"

    @property
    def inference_available(self) -> bool:
        return self.adapter.initialized

    def __init__(
        self,
        *,
        model_path=None,
        device=None,
        confidence_threshold=None,
        keypoint_threshold=None,
    ) -> None:
        from vision.rtmo import RTMOAdapter, RTMOConfig, RTMOConfigurationError
        from vision.tracking import IoUPersonTracker

        from django.conf import settings

        path = Path(
            model_path
            if model_path is not None
            else getattr(settings, "VISION_MODEL_PATH", "model-artifacts/vision/rtmo-s/model.onnx")
        ).expanduser()
        requested_device = device or getattr(settings, "VISION_DEVICE", "cpu")
        threshold = (
            getattr(settings, "VISION_CONFIDENCE_THRESHOLD", 0.25)
            if confidence_threshold is None
            else confidence_threshold
        )
        keypoint_score = (
            getattr(settings, "VISION_KEYPOINT_THRESHOLD", 0.2)
            if keypoint_threshold is None
            else keypoint_threshold
        )
        self.config = RTMOConfig(
            model_path=path,
            device=requested_device,
            confidence_threshold=float(threshold),
            keypoint_threshold=float(keypoint_score),
        )
        self.adapter = RTMOAdapter(self.config)
        self.adapter.tracks = IoUPersonTracker()
        self._configuration_error = RTMOConfigurationError

    @property
    def model_name(self) -> str:
        return self.adapter.model_name

    @property
    def model_version(self) -> str | None:
        return self.adapter.model_version

    @property
    def artifact_sha256(self) -> str | None:
        return self.adapter.artifact_sha256

    def build_pipeline(self) -> VisionPipeline:
        from time import perf_counter

        started = perf_counter()
        try:
            self.adapter.initialize()
        except self._configuration_error as exc:
            LOGGER.error(
                "vision.model_initialization_failed provider=%s model=%s device=%s error=%s",
                self.name,
                self.model_name,
                self.config.device,
                str(exc),
            )
            raise
        LOGGER.info(
            "vision.provider_ready provider=%s model=%s device=%s confidence_threshold=%.3f initialization_seconds=%.3f",
            self.name,
            self.model_name,
            self.config.device,
            self.config.confidence_threshold,
            perf_counter() - started,
        )
        stages = _RTMOCompatibleAdapter(self.adapter)
        return VisionPipeline(
            detector=stages,
            tracker=stages,
            pose_estimator=stages,
            classifier=stages,
            verifier=FallTemporalVerifier(),
        )


class DevelopmentNullVisionProvider:
    """A runnable development adapter that emits no detections or events."""

    name = "development-null"
    inference_available = False

    def build_pipeline(self) -> VisionPipeline:
        """Build the real pipeline around an explicitly empty detection stage."""
        return VisionPipeline(
            detector=_NoDetections(),
            tracker=_NoTracks(),
            pose_estimator=_UnavailablePoseEstimator(),
            classifier=_UnavailableActivityClassifier(),
            verifier=FallTemporalVerifier(),
        )
