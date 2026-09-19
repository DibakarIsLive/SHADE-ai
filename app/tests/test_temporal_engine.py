from datetime import datetime, timedelta, timezone

from vision.temporal import FallTemporalVerifier, TemporalVerifierConfig
from vision.types import ActivityObservation, PoseSignal


def observation(activity: str, observed_at: datetime, confidence: float = 0.9) -> ActivityObservation:
    return ActivityObservation(
        track_id="person-01",
        activity=activity,
        confidence=confidence,
        pose=PoseSignal(
            posture=activity,
            verticality=0.8 if activity in {"standing", "walking"} else 0.2,
            motion_score=0.6 if activity == "walking" else 0.1,
        ),
        observed_at=observed_at,
    )


def test_single_low_posture_observation_is_not_verified():
    verifier = FallTemporalVerifier()
    now = datetime.now(timezone.utc)

    decision = verifier.observe(observation("lying", now))

    assert decision.verified is False
    assert decision.event_type is None
    assert decision.observation_count == 1
    assert "insufficient" in decision.reason


def test_upright_to_sustained_low_posture_is_verified():
    verifier = FallTemporalVerifier(
        TemporalVerifierConfig(
            minimum_observations=3,
            minimum_duration_seconds=0.5,
            minimum_confidence=0.65,
        )
    )
    start = datetime.now(timezone.utc)

    verifier.observe(observation("standing", start))
    verifier.observe(observation("falling", start + timedelta(seconds=0.4)))
    decision = verifier.observe(observation("lying", start + timedelta(seconds=0.9)))

    assert decision.verified is True
    assert decision.event_type == "fall"
    assert decision.observation_count == 3
    assert decision.duration_seconds == 0.9
    assert decision.confidence == 0.9


def test_low_confidence_sequence_does_not_trigger():
    verifier = FallTemporalVerifier()
    start = datetime.now(timezone.utc)

    verifier.observe(observation("walking", start, confidence=0.9))
    verifier.observe(observation("falling", start + timedelta(seconds=0.4), confidence=0.61))
    decision = verifier.observe(observation("lying", start + timedelta(seconds=0.9), confidence=0.9))

    assert decision.verified is False
    assert decision.event_type is None
