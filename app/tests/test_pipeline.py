from datetime import datetime, timedelta, timezone

from vision.pipeline import VisionPipeline
from vision.temporal import FallTemporalVerifier
from vision.types import ActivityObservation, BoundingBox, Detection, Frame, PoseSignal, Track


class SequenceDetector:
    def detect(self, frame):  # noqa: ARG002
        return [
            Detection(
                label="person",
                confidence=0.98,
                bounding_box=BoundingBox(left=10, top=10, right=100, bottom=180),
            )
        ]


class StableTracker:
    def update(self, detections, frame):  # noqa: ARG002
        if not detections:
            return []
        return [Track(track_id="person-01", detection=detections[0], age_frames=frame.frame_number + 1)]


class FixedPoseEstimator:
    def estimate(self, frame, track):  # noqa: ARG002
        return PoseSignal(posture="unknown", verticality=0.5, motion_score=0.2)


class SequenceClassifier:
    activities = ("standing", "falling", "lying")

    def classify(self, track, pose, frame):  # noqa: ARG002
        activity = self.activities[min(frame.frame_number, len(self.activities) - 1)]
        return ActivityObservation(
            track_id=track.track_id,
            activity=activity,
            confidence=0.9,
            pose=pose,
            observed_at=frame.captured_at,
        )


def test_pipeline_composes_all_stages_and_verifies_sequence():
    pipeline = VisionPipeline(
        detector=SequenceDetector(),
        tracker=StableTracker(),
        pose_estimator=FixedPoseEstimator(),
        classifier=SequenceClassifier(),
        verifier=FallTemporalVerifier(),
    )
    start = datetime.now(timezone.utc)

    results = [
        pipeline.process(
            Frame(
                frame_number=index,
                captured_at=start + timedelta(seconds=seconds),
                payload=None,
                width=1280,
                height=720,
            )
        )
        for index, seconds in enumerate((0.0, 0.4, 0.9))
    ]

    assert [result.frame_number for result in results] == [0, 1, 2]
    assert all(len(result.observations) == 1 for result in results)
    assert results[-1].observations[0].activity == "lying"
    assert results[-1].decisions[0].verified is True
    assert pipeline.last_result is results[-1]


def test_pipeline_returns_empty_result_when_no_person_is_detected():
    class EmptyDetector:
        def detect(self, frame):  # noqa: ARG002
            return []

    pipeline = VisionPipeline(
        detector=EmptyDetector(),
        tracker=StableTracker(),
        pose_estimator=FixedPoseEstimator(),
        classifier=SequenceClassifier(),
        verifier=FallTemporalVerifier(),
    )

    result = pipeline.process(Frame(frame_number=4, captured_at=datetime.now(timezone.utc)))

    assert result.observations == []
    assert result.decisions == []
    assert result.frame_number == 4
