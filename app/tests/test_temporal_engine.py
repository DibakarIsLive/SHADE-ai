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


def test_expired_track_cleanup_prevents_old_temporal_evidence_from_leaking():
    verifier = FallTemporalVerifier()
    start = datetime.now(timezone.utc)
    verifier.observe(observation("standing", start))
    verifier.observe(observation("falling", start + timedelta(seconds=0.4)))

    verifier.retain_track_ids(frozenset())
    restarted_track = verifier.observe(observation("lying", start + timedelta(seconds=0.9)))

    assert restarted_track.verified is False
    assert restarted_track.observation_count == 1


def test_temporal_history_remains_bounded_when_track_ids_churn():
    verifier = FallTemporalVerifier()
    start = datetime.now(timezone.utc)

    for index in range(1000):
        track_id = f"ephemeral-{index}"
        verifier.observe(
            ActivityObservation(
                track_id=track_id,
                activity="standing",
                confidence=0.9,
                pose=PoseSignal("standing", 0.9, 0.0),
                observed_at=start + timedelta(milliseconds=index),
            )
        )
        verifier.retain_track_ids(frozenset({track_id}))

    assert len(verifier._history) == 1
    assert set(verifier._history) == {"ephemeral-999"}


def test_normal_standing_and_walking_sequence_does_not_verify():
    verifier = FallTemporalVerifier()
    start = datetime.now(timezone.utc)

    decisions = [
        verifier.observe(observation(activity, start + timedelta(seconds=offset)))
        for activity, offset in (("standing", 0.0), ("walking", 0.4), ("standing", 0.9))
    ]

    assert all(decision.verified is False for decision in decisions)
    assert all(decision.event_type is None for decision in decisions)


def test_two_observations_do_not_verify_even_when_duration_is_sufficient():
    verifier = FallTemporalVerifier()
    start = datetime.now(timezone.utc)

    verifier.observe(observation("standing", start))
    decision = verifier.observe(observation("lying", start + timedelta(seconds=0.9)))

    assert decision.verified is False
    assert decision.observation_count == 2


def test_insufficient_duration_does_not_verify_sustained_low_posture():
    verifier = FallTemporalVerifier()
    start = datetime.now(timezone.utc)

    verifier.observe(observation("standing", start))
    verifier.observe(observation("falling", start + timedelta(seconds=0.1)))
    decision = verifier.observe(observation("lying", start + timedelta(seconds=0.2)))

    assert decision.verified is False
    assert decision.duration_seconds == 0.2


def test_low_posture_without_prior_upright_transition_does_not_verify():
    verifier = FallTemporalVerifier()
    start = datetime.now(timezone.utc)

    verifier.observe(observation("falling", start))
    verifier.observe(observation("lying", start + timedelta(seconds=0.4)))
    decision = verifier.observe(observation("lying", start + timedelta(seconds=0.9)))

    assert decision.verified is False
    assert decision.event_type is None


def test_upright_recovery_clears_recent_low_posture_evidence():
    verifier = FallTemporalVerifier()
    start = datetime.now(timezone.utc)

    verifier.observe(observation("standing", start))
    verifier.observe(observation("falling", start + timedelta(seconds=0.4)))
    verified = verifier.observe(observation("lying", start + timedelta(seconds=0.9)))
    recovered = verifier.observe(observation("standing", start + timedelta(seconds=1.4)))
    continuing_upright = verifier.observe(observation("walking", start + timedelta(seconds=1.8)))

    assert verified.verified is True
    assert recovered.verified is False
    assert continuing_upright.verified is False


def test_fresh_sustained_low_sequence_can_verify_after_upright_recovery():
    verifier = FallTemporalVerifier()
    start = datetime.now(timezone.utc)

    verifier.observe(observation("standing", start))
    verifier.observe(observation("falling", start + timedelta(seconds=0.4)))
    assert verifier.observe(observation("lying", start + timedelta(seconds=0.9))).verified is True
    assert verifier.observe(observation("standing", start + timedelta(seconds=1.4))).verified is False
    assert verifier.observe(observation("walking", start + timedelta(seconds=1.8))).verified is False
    assert verifier.observe(observation("falling", start + timedelta(seconds=2.2))).verified is False
    rearmed = verifier.observe(observation("lying", start + timedelta(seconds=2.7)))

    assert rearmed.verified is True
    assert rearmed.event_type == "fall"
