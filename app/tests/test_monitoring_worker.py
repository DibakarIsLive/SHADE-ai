from __future__ import annotations

from datetime import datetime, timedelta, timezone
import threading

import pytest

from monitoring.worker import MonitoringWorker, MonitoringWorkerError
from vision.pipeline import PipelineResult, VisionPipeline
from vision.providers import DevelopmentNullVisionProvider
from vision.sources import IterableFrameSource
from vision.temporal import FallTemporalVerifier
from vision.types import (
    ActivityObservation,
    BoundingBox,
    Detection,
    Frame,
    PoseSignal,
    Track,
)


class SequenceDetector:
    def detect(self, frame: Frame):  # noqa: ARG002
        return [
            Detection(
                label="person",
                confidence=0.9,
                bounding_box=BoundingBox(0, 0, 12, 24),
            )
        ]


class StableTracker:
    def __init__(self):
        self._retained_track_ids = frozenset()

    @property
    def retained_track_ids(self):
        return self._retained_track_ids

    def update(self, detections, frame):
        if not detections:
            self._retained_track_ids = frozenset()
            return []
        self._retained_track_ids = frozenset({"test-track"})
        return [Track(track_id="test-track", detection=detections[0], age_frames=frame.frame_number + 1)]


class FixedPoseEstimator:
    def estimate(self, frame, track):  # noqa: ARG002
        return PoseSignal(posture="sequence", verticality=0.5, motion_score=0.1)


class SequenceClassifier:
    def classify(self, track, pose, frame):  # noqa: ARG002
        activities = ("standing", "falling", "lying", "lying")
        return ActivityObservation(
            track_id=track.track_id,
            activity=activities[min(frame.frame_number, len(activities) - 1)],
            confidence=0.9,
            pose=pose,
            observed_at=frame.captured_at,
            metadata={
                "vision_provider": "test-model-adapter",
                "model": "deterministic-test-observations",
                "model_confidence": 0.9,
            },
        )


def temporal_pipeline() -> VisionPipeline:
    return VisionPipeline(
        detector=SequenceDetector(),
        tracker=StableTracker(),
        pose_estimator=FixedPoseEstimator(),
        classifier=SequenceClassifier(),
        verifier=FallTemporalVerifier(),
    )


def deterministic_frames(count: int = 4) -> list[Frame]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Frame(
            frame_number=index,
            captured_at=start + timedelta(seconds=(0.0, 0.4, 0.9, 1.4)[index]),
            width=32,
            height=24,
        )
        for index in range(count)
    ]


def test_worker_processes_frames_and_releases_source_on_normal_shutdown():
    source = IterableFrameSource(deterministic_frames())
    worker = MonitoringWorker(
        source,
        DevelopmentNullVisionProvider().build_pipeline(),
        provider_name="development-null",
        inference_available=False,
    )

    processed = worker.run()

    assert processed == 4
    assert source.end_of_stream is True
    assert source.closed is True
    assert source.is_opened is False
    assert worker.running is False
    assert worker.pipeline.last_result is not None
    assert worker.pipeline.last_result.observations == []


def test_worker_reports_source_ready_only_after_successful_open():
    class ReadinessSource(IterableFrameSource):
        def __init__(self, frames):
            super().__init__(frames)
            self.open_completed = False

        def open(self):
            super().open()
            self.open_completed = True

    source = ReadinessSource(deterministic_frames())
    readiness = []
    worker = MonitoringWorker(
        source,
        DevelopmentNullVisionProvider().build_pipeline(),
        inference_available=False,
        on_source_opened=lambda: readiness.append(source.open_completed),
    )

    assert worker.run(max_frames=1) == 1
    assert readiness == [True]
    assert source.closed is True


def test_worker_does_not_report_source_ready_when_open_fails():
    source = IterableFrameSource(deterministic_frames())
    readiness = []

    def fail_to_open():
        raise RuntimeError("source open failed")

    source.open = fail_to_open
    worker = MonitoringWorker(
        source,
        DevelopmentNullVisionProvider().build_pipeline(),
        inference_available=False,
        on_source_opened=lambda: readiness.append(True),
    )

    with pytest.raises(RuntimeError, match="source open failed"):
        worker.run()

    assert readiness == []
    assert worker.running is False


def test_worker_honors_a_graceful_shutdown_request_between_frames():
    source = IterableFrameSource(deterministic_frames())
    stop_event = threading.Event()

    class StopsAfterFirstFrame:
        last_result = None

        def process(self, frame):
            result = PipelineResult(frame_number=frame.frame_number)
            self.last_result = result
            stop_event.set()
            return result

    worker = MonitoringWorker(
        source,
        StopsAfterFirstFrame(),
        stop_event=stop_event,
        inference_available=False,
    )

    assert worker.run() == 1
    assert source.closed is True
    assert worker.running is False


def test_worker_honors_frame_limit_and_closes_source():
    source = IterableFrameSource(deterministic_frames())
    worker = MonitoringWorker(
        source,
        DevelopmentNullVisionProvider().build_pipeline(),
        inference_available=False,
    )

    assert worker.run(max_frames=2) == 2
    assert source.closed is True


def test_worker_closes_source_if_processing_fails():
    source = IterableFrameSource(deterministic_frames())

    class FailedPipeline:
        last_result = None

        def process(self, frame):  # noqa: ARG002
            raise RuntimeError("pipeline unavailable")

    worker = MonitoringWorker(source, FailedPipeline())

    with pytest.raises(RuntimeError, match="pipeline unavailable"):
        worker.run()

    assert source.closed is True
    assert worker.running is False


def test_worker_persists_only_temporally_verified_results_once_per_track():
    created_events = []
    source = IterableFrameSource(deterministic_frames())
    worker = MonitoringWorker(
        source,
        temporal_pipeline(),
        camera_id="configured-video-camera",
        provider_name="test-model-adapter",
        model_name="deterministic-test-observations",
        source_type="video_file",
        inference_available=True,
        event_persister=created_events.append,
    )

    assert worker.run() == 4

    assert len(created_events) == 1
    event = created_events[0]
    assert event["event_type"] == "fall"
    assert event["severity"] == "critical"
    assert event["status"] == "verified"
    assert event["camera_id"] == "configured-video-camera"
    assert event["track_id"] == "test-track"
    assert event["confidence"] == 0.9
    assert event["duration_seconds"] == pytest.approx(0.9)
    assert event["frame_count"] == 3
    assert event["occurred_at"] == deterministic_frames()[2].captured_at
    assert event["context"]["vision_provider"] == "test-model-adapter"
    assert event["context"]["model"] == "deterministic-test-observations"
    assert event["context"]["model_confidence"] == pytest.approx(0.9)
    assert event["context"]["source_type"] == "video_file"
    assert event["context"]["frame_number"] == 2
    assert event["provenance"] == {
        "provider": "test-model-adapter",
        "model_identifier": "deterministic-test-observations",
        "model_version": None,
        "artifact_sha256": None,
        "source_type": "video_file",
        "camera_id": "configured-video-camera",
        "processed_at": event["provenance"]["processed_at"],
    }
    assert event["provenance"]["processed_at"].tzinfo is not None
    assert source.closed is True
    assert worker.last_run_summary is not None
    assert worker.last_run_summary["frames_processed"] == 4
    assert worker.last_run_summary["observations"] == 4
    assert worker.last_run_summary["unique_tracks"] == 1
    assert worker.last_run_summary["temporal_decisions"] == 4
    assert worker.last_run_summary["verified_decisions"] == 2
    assert worker.last_run_summary["persisted_events"] == 1


def test_duplicate_suppression_rearms_only_after_upright_activity():
    created_events = []
    worker = MonitoringWorker(
        IterableFrameSource(deterministic_frames()),
        temporal_pipeline(),
        camera_id="configured-video-camera",
        provider_name="test-model-adapter",
        model_name="deterministic-test-observations",
        source_type="video_file",
        inference_available=True,
        event_persister=created_events.append,
    )

    assert worker.run() == 4
    assert len(created_events) == 1
    result = worker.pipeline.last_result
    assert result is not None and result.decisions[0].verified
    assert worker._persist_verified_events(result) == 0

    # An upright observation signifies the end of this episode. A later
    # verifier-approved fall decision for the same track may then be persisted.
    upright = ActivityObservation(
        track_id="test-track",
        activity="standing",
        confidence=0.9,
        pose=PoseSignal(posture="standing", verticality=0.9, motion_score=0.0),
        observed_at=deterministic_frames()[3].captured_at,
        metadata={
            "vision_provider": "test-model-adapter",
            "model": "deterministic-test-observations",
            "model_confidence": 0.9,
        },
    )
    worker._persist_verified_events(
        PipelineResult(frame_number=4, observations=[upright])
    )
    assert worker._persist_verified_events(result) == 1
    assert len(created_events) == 2


def test_development_null_provider_cannot_create_synthetic_detections_or_events():
    provider = DevelopmentNullVisionProvider()
    created_events = []
    worker = MonitoringWorker(
        IterableFrameSource(deterministic_frames()),
        provider.build_pipeline(),
        camera_id="configured-video-camera",
        provider_name=provider.name,
        inference_available=provider.inference_available,
        event_persister=created_events.append,
    )

    assert provider.name == "development-null"
    assert provider.inference_available is False
    assert worker.run() == 4
    assert created_events == []
    assert worker.pipeline.last_result is not None
    assert worker.pipeline.last_result.observations == []
    assert worker.pipeline.last_result.decisions == []


def test_worker_reports_event_persistence_failure_and_still_closes_source():
    source = IterableFrameSource(deterministic_frames())

    def fail_persistence(_data):
        raise OSError("database unavailable")

    worker = MonitoringWorker(
        source,
        temporal_pipeline(),
        camera_id="configured-video-camera",
        inference_available=True,
        event_persister=fail_persistence,
    )

    with pytest.raises(MonitoringWorkerError, match="persistence failed"):
        worker.run()

    assert source.closed is True
    assert worker.running is False


def test_verified_decision_without_persistence_service_fails_truthfully():
    source = IterableFrameSource(deterministic_frames())
    worker = MonitoringWorker(
        source,
        temporal_pipeline(),
        camera_id="configured-video-camera",
        inference_available=True,
    )

    with pytest.raises(MonitoringWorkerError, match="no event persistence service"):
        worker.run()

    assert source.closed is True


def test_invalid_worker_limits_are_rejected():
    worker = MonitoringWorker(
        IterableFrameSource(deterministic_frames()),
        DevelopmentNullVisionProvider().build_pipeline(),
        inference_available=False,
    )

    with pytest.raises(ValueError, match="greater than zero"):
        worker.run(max_frames=0)

    assert worker.source.closed is False
