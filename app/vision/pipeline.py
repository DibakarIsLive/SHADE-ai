"""Frame-to-activity orchestration without a vendor-specific model dependency."""

from __future__ import annotations

from dataclasses import dataclass, field

from vision.interfaces import ActivityClassifier, PersonDetector, PersonTracker, PoseEstimator, TemporalVerifier
from vision.types import ActivityObservation, Frame, VerificationDecision


@dataclass
class PipelineResult:
    frame_number: int
    observations: list[ActivityObservation] = field(default_factory=list)
    decisions: list[VerificationDecision] = field(default_factory=list)


class VisionPipeline:
    """Compose detector, tracker, pose, activity, and temporal stages."""

    def __init__(
        self,
        detector: PersonDetector,
        tracker: PersonTracker,
        pose_estimator: PoseEstimator,
        classifier: ActivityClassifier,
        verifier: TemporalVerifier,
    ) -> None:
        self.detector = detector
        self.tracker = tracker
        self.pose_estimator = pose_estimator
        self.classifier = classifier
        self.verifier = verifier
        self.last_result: PipelineResult | None = None

    def process(self, frame: Frame) -> PipelineResult:
        detections = self.detector.detect(frame)
        tracks = self.tracker.update(detections, frame)
        observations: list[ActivityObservation] = []
        decisions: list[VerificationDecision] = []
        for track in tracks:
            pose = self.pose_estimator.estimate(frame, track)
            observation = self.classifier.classify(track, pose, frame)
            observations.append(observation)
            decisions.append(self.verifier.observe(observation))
        self.last_result = PipelineResult(frame.frame_number, observations, decisions)
        return self.last_result
