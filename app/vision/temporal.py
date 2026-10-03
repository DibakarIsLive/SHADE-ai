"""Temporal fall verification with a conservative multi-observation rule."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import timedelta

from vision.types import ActivityObservation, VerificationDecision


@dataclass
class TemporalVerifierConfig:
    minimum_observations: int = 3
    minimum_duration_seconds: float = 0.5
    minimum_confidence: float = 0.65
    history_size: int = 30


class FallTemporalVerifier:
    """Verify a fall only after a posture transition and sustained low posture."""

    def __init__(self, config: TemporalVerifierConfig | None = None) -> None:
        self.config = config or TemporalVerifierConfig()
        self._history: dict[str, deque[ActivityObservation]] = defaultdict(
            lambda: deque(maxlen=self.config.history_size)
        )

    def observe(self, observation: ActivityObservation) -> VerificationDecision:
        history = self._history[observation.track_id]
        history.append(observation)
        recent = list(history)
        duration = (
            recent[-1].observed_at - recent[0].observed_at
        ).total_seconds() if len(recent) > 1 else 0.0
        has_upright = any(item.activity in {"standing", "walking", "running"} for item in recent[:-1])
        low_posture_count = sum(
            item.activity in {"falling", "lying", "motionless"} for item in recent[-2:]
        )
        confidence = min(item.confidence for item in recent) if recent else 0.0
        verified = (
            len(recent) >= self.config.minimum_observations
            and duration >= self.config.minimum_duration_seconds
            and has_upright
            and low_posture_count >= 2
            and confidence >= self.config.minimum_confidence
        )
        reason = (
            "upright-to-low-posture transition sustained across temporal history"
            if verified
            else "insufficient temporal evidence for fall verification"
        )
        return VerificationDecision(
            verified=verified,
            event_type="fall" if verified else None,
            confidence=confidence,
            reason=reason,
            observation_count=len(recent),
            duration_seconds=duration,
        )

    def reset(self, track_id: str) -> None:
        self._history.pop(track_id, None)

    def retain_track_ids(self, track_ids: frozenset[str]) -> None:
        """Release temporal history for trajectories the tracker has expired."""
        for track_id in self._history.keys() - track_ids:
            self.reset(track_id)
