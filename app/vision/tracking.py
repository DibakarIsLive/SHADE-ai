"""Small, camera-local IoU association for temporal observation continuity."""

from __future__ import annotations

from dataclasses import dataclass

from vision.types import BoundingBox, Detection, Frame, Track


@dataclass
class _TrackState:
    track_id: str
    detection: Detection
    age_frames: int = 1
    missed_frames: int = 0


class IoUPersonTracker:
    """Associate nearby person boxes; IDs are ephemeral worker-local track IDs."""

    def __init__(self, *, iou_threshold: float = 0.3, max_missed_frames: int = 2) -> None:
        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0 and 1")
        if max_missed_frames < 0:
            raise ValueError("max_missed_frames must not be negative")
        self.iou_threshold = float(iou_threshold)
        self.max_missed_frames = int(max_missed_frames)
        self._tracks: dict[str, _TrackState] = {}
        self._next_track_number = 1

    @property
    def active_tracks(self) -> tuple[Track, ...]:
        """Tracks observed in the most recent frame (not missed-frame memory)."""
        return tuple(
            Track(state.track_id, state.detection, state.age_frames)
            for state in self._tracks.values()
            if state.missed_frames == 0
        )

    @property
    def retained_track_ids(self) -> frozenset[str]:
        """IDs still eligible for association, including missed-frame grace state."""
        return frozenset(self._tracks)

    def update(self, detections: list[Detection], frame: Frame) -> list[Track]:  # noqa: ARG002
        """Greedily match each box at most once using intersection over union."""
        previous = self._tracks
        candidates = sorted(
            (
                self._intersection_over_union(state.detection.bounding_box, detection.bounding_box),
                track_id,
                detection_index,
            )
            for track_id, state in previous.items()
            for detection_index, detection in enumerate(detections)
        )
        matched_tracks: set[str] = set()
        matched_detections: set[int] = set()
        assignments: dict[int, _TrackState] = {}
        for overlap, track_id, detection_index in reversed(candidates):
            if overlap < self.iou_threshold:
                break
            if track_id in matched_tracks or detection_index in matched_detections:
                continue
            matched_tracks.add(track_id)
            matched_detections.add(detection_index)
            assignments[detection_index] = previous[track_id]

        next_states: dict[str, _TrackState] = {}
        output: list[Track] = []
        for detection_index, detection in enumerate(detections):
            state = assignments.get(detection_index)
            if state is None:
                track_id = f"local-track-{self._next_track_number:06d}"
                self._next_track_number += 1
                state = _TrackState(track_id=track_id, detection=detection)
            else:
                state = _TrackState(
                    track_id=state.track_id,
                    detection=detection,
                    age_frames=state.age_frames + 1,
                )
            next_states[state.track_id] = state
            output.append(Track(state.track_id, detection, state.age_frames))

        for track_id, state in previous.items():
            if track_id in matched_tracks:
                continue
            missed = state.missed_frames + 1
            if missed <= self.max_missed_frames:
                next_states[track_id] = _TrackState(
                    track_id=state.track_id,
                    detection=state.detection,
                    age_frames=state.age_frames,
                    missed_frames=missed,
                )

        self._tracks = next_states
        return output

    @staticmethod
    def _intersection_over_union(left: BoundingBox, right: BoundingBox) -> float:
        intersection_width = max(0.0, min(left.right, right.right) - max(left.left, right.left))
        intersection_height = max(0.0, min(left.bottom, right.bottom) - max(left.top, right.top))
        intersection = intersection_width * intersection_height
        union = left.width * left.height + right.width * right.height - intersection
        return intersection / union if union > 0.0 else 0.0
