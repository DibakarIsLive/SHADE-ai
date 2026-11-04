"""Long-running frame orchestration kept outside Django HTTP requests."""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from vision.interfaces import CameraSource
from vision.pipeline import PipelineResult, VisionPipeline
from vision.sources import VideoSourceError


LOGGER = logging.getLogger(__name__)
_MAX_REMEMBERED_EVENTS = 4096


class MonitoringWorkerError(RuntimeError):
    """The configured worker cannot safely complete a verified decision."""


class MonitoringWorker:
    """Open a configured source, run the analysis pipeline, and release resources."""

    def __init__(
        self,
        source: CameraSource,
        pipeline: VisionPipeline,
        *,
        camera_id: str = "",
        camera_name: str = "",
        provider_name: str = "unspecified",
        model_name: str = "",
        model_version: str | None = None,
        artifact_sha256: str | None = None,
        source_type: str = "unspecified",
        inference_available: bool = True,
        event_persister: Callable[[dict[str, Any]], Any] | None = None,
        stop_event: threading.Event | None = None,
        on_source_opened: Callable[[], None] | None = None,
    ) -> None:
        self.source = source
        self.pipeline = pipeline
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.provider_name = provider_name
        self.model_name = model_name
        self.model_version = model_version
        self.artifact_sha256 = artifact_sha256
        self.source_type = source_type
        self.inference_available = inference_available
        self.event_persister = event_persister
        self.stop_event = stop_event or threading.Event()
        self.on_source_opened = on_source_opened
        self.running = False
        self._persisted_event_keys: OrderedDict[tuple[str, str], None] = OrderedDict()
        self.last_run_summary: dict[str, int | float] | None = None

    def run(self, max_frames: int | None = None) -> int:
        """Process frames until EOF, a frame limit, or a graceful-stop request."""
        if max_frames is not None and max_frames < 1:
            raise ValueError("max_frames must be greater than zero")
        if self.running:
            raise MonitoringWorkerError("This monitoring worker is already running.")

        self.running = True
        processed = 0
        observation_count = 0
        tracks_started = 0
        temporal_decision_count = 0
        verified_decision_count = 0
        persisted_event_count = 0
        started_at = time.monotonic()
        LOGGER.info(
            "monitor.worker_starting camera_id=%s camera_name=%s source_type=%s provider=%s model=%s inference_available=%s",
            self.camera_id or "unspecified",
            self.camera_name or "unspecified",
            self.source_type,
            self.provider_name,
            self.model_name or "unspecified",
            self.inference_available,
        )
        if not self.inference_available:
            LOGGER.warning(
                "monitor.inference_unavailable camera_id=%s provider=%s; no real detections or events can be produced",
                self.camera_id or "unspecified",
                self.provider_name,
            )

        primary_error: BaseException | None = None
        try:
            self.source.open()
            if self.on_source_opened is not None:
                self.on_source_opened()
            LOGGER.info(
                "monitor.source_opened camera_id=%s width=%s height=%s source_fps=%s",
                self.camera_id or "unspecified",
                self.source.width,
                self.source.height,
                self.source.fps,
            )
            LOGGER.info(
                "monitor.processing_started camera_id=%s provider=%s",
                self.camera_id or "unspecified",
                self.provider_name,
            )

            frames = iter(self.source.frames())
            while not self.stop_event.is_set():
                if max_frames is not None and processed >= max_frames:
                    break
                try:
                    frame = next(frames)
                except StopIteration:
                    break

                result = self.pipeline.process(frame)
                processed += 1
                observation_count += len(result.observations)
                tracks_started += result.tracks_started
                temporal_decision_count += len(result.decisions)
                verified_decision_count += sum(decision.verified for decision in result.decisions)
                persisted_event_count += self._persist_verified_events(result)
                LOGGER.debug(
                    "monitor.frame_processed camera_id=%s frame_number=%s frames_processed=%s",
                    self.camera_id or "unspecified",
                    frame.frame_number,
                    processed,
                )
        except VideoSourceError as exc:
            primary_error = exc
            LOGGER.exception(
                "monitor.source_failure camera_id=%s error_type=%s",
                self.camera_id or "unspecified",
                type(exc).__name__,
            )
            raise
        except BaseException as exc:
            primary_error = exc
            LOGGER.exception(
                "monitor.worker_failure camera_id=%s error_type=%s",
                self.camera_id or "unspecified",
                type(exc).__name__,
            )
            raise
        finally:
            self.running = False
            try:
                self.source.close()
            except Exception:
                LOGGER.exception(
                    "monitor.source_release_failure camera_id=%s",
                    self.camera_id or "unspecified",
                )
                if primary_error is None:
                    raise
            elapsed = max(time.monotonic() - started_at, 0.0)
            approximate_fps = processed / elapsed if elapsed > 0 else 0.0
            self.last_run_summary = {
                "frames_processed": processed,
                "observations": observation_count,
                "unique_tracks": tracks_started,
                "temporal_decisions": temporal_decision_count,
                "verified_decisions": verified_decision_count,
                "persisted_events": persisted_event_count,
                "elapsed_seconds": elapsed,
                "approximate_fps": approximate_fps,
            }
            LOGGER.info(
                "monitor.run_summary camera_id=%s frames_processed=%s observations=%s unique_tracks=%s temporal_decisions=%s verified_decisions=%s persisted_events=%s elapsed_seconds=%.3f approximate_fps=%.3f",
                self.camera_id or "unspecified",
                processed,
                observation_count,
                tracks_started,
                temporal_decision_count,
                verified_decision_count,
                persisted_event_count,
                elapsed,
                approximate_fps,
            )
            LOGGER.info(
                "monitor.processing_stopped camera_id=%s frames_processed=%s elapsed_seconds=%.3f approximate_fps=%.3f end_of_stream=%s stop_requested=%s",
                self.camera_id or "unspecified",
                processed,
                elapsed,
                approximate_fps,
                getattr(self.source, "end_of_stream", False),
                self.stop_event.is_set(),
            )
            LOGGER.info(
                "monitor.graceful_shutdown camera_id=%s frames_processed=%s",
                self.camera_id or "unspecified",
                processed,
            )
        return processed

    def _persist_verified_events(self, result: PipelineResult) -> int:
        """Persist verified decisions once per fall episode, re-arming after upright activity."""
        if not self.inference_available:
            return 0

        for observation in result.observations:
            if observation.activity in {"standing", "walking", "running"}:
                self._persisted_event_keys.pop((observation.track_id, "fall"), None)
        if not result.decisions:
            return 0

        persisted_count = 0
        for observation, decision in zip(result.observations, result.decisions, strict=False):
            if not decision.verified or not decision.event_type:
                continue

            if not self.camera_id:
                raise MonitoringWorkerError(
                    "A camera_id is required before persisting a verified event."
                )
            if self.event_persister is None:
                raise MonitoringWorkerError(
                    "A verified decision was produced but no event persistence service is configured."
                )

            track_id = observation.track_id
            event_type = decision.event_type
            LOGGER.info(
                "monitor.event_generated camera_id=%s track_id=%s event_type=%s confidence=%.4f duration_seconds=%.3f",
                self.camera_id,
                track_id,
                event_type,
                float(decision.confidence),
                float(decision.duration_seconds),
            )
            event_key = (track_id, event_type)
            if event_key in self._persisted_event_keys:
                LOGGER.debug(
                    "monitor.duplicate_event_suppressed camera_id=%s track_id=%s event_type=%s",
                    self.camera_id,
                    track_id,
                    event_type,
                )
                continue

            confidence = float(decision.confidence)
            duration_seconds = float(decision.duration_seconds)
            if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise MonitoringWorkerError("Verified event confidence must be between 0 and 1.")
            if not math.isfinite(duration_seconds) or duration_seconds < 0.0:
                raise MonitoringWorkerError("Verified event duration must be a finite non-negative value.")

            occurred_at = observation.observed_at
            if not isinstance(occurred_at, datetime):
                raise MonitoringWorkerError("Verified event timestamp is invalid.")

            observation_metadata = getattr(observation, "metadata", {})
            if not isinstance(observation_metadata, dict):
                raise MonitoringWorkerError("Verified event observation provenance is invalid.")
            try:
                model_confidence = float(
                    observation_metadata.get("model_confidence", observation.confidence)
                )
            except (TypeError, ValueError) as exc:
                raise MonitoringWorkerError("Model confidence provenance is invalid.") from exc
            if not math.isfinite(model_confidence) or not 0.0 <= model_confidence <= 1.0:
                raise MonitoringWorkerError("Model confidence provenance must be between 0 and 1.")
            model_identifier = observation_metadata.get("model", self.model_name or None)
            if model_identifier is not None and (
                not isinstance(model_identifier, str) or not model_identifier.strip()
            ):
                raise MonitoringWorkerError("Model identifier provenance is invalid.")
            if isinstance(model_identifier, str):
                model_identifier = model_identifier.strip()

            event_data = {
                "event_type": event_type,
                "severity": "critical" if event_type == "fall" else "warning",
                "status": "verified",
                "camera_id": self.camera_id,
                "track_id": track_id,
                "confidence": confidence,
                "duration_seconds": duration_seconds,
                "frame_count": max(0, int(decision.observation_count)),
                "occurred_at": occurred_at,
                "context": {
                    "decision_reason": str(decision.reason)[:500],
                    "vision_provider": self.provider_name[:120],
                    "model": (model_identifier or "unspecified")[:200],
                    "model_confidence": model_confidence,
                    "source_type": self.source_type[:40],
                    "frame_number": result.frame_number,
                },
                "provenance": {
                    "provider": self.provider_name,
                    "model_identifier": model_identifier,
                    "model_version": self.model_version,
                    "artifact_sha256": self.artifact_sha256,
                    "source_type": self.source_type,
                    "camera_id": self.camera_id,
                    "processed_at": datetime.now(timezone.utc),
                },
            }
            try:
                self.event_persister(event_data)
            except Exception as exc:
                LOGGER.exception(
                    "monitor.event_persistence_failure camera_id=%s track_id=%s event_type=%s",
                    self.camera_id,
                    track_id,
                    event_type,
                )
                raise MonitoringWorkerError(
                    "Verified event persistence failed; the event was not reported as saved."
                ) from exc

            persisted_count += 1
            self._persisted_event_keys[event_key] = None
            self._persisted_event_keys.move_to_end(event_key)
            if len(self._persisted_event_keys) > _MAX_REMEMBERED_EVENTS:
                self._persisted_event_keys.popitem(last=False)
            LOGGER.info(
                "monitor.event_persisted camera_id=%s track_id=%s event_type=%s status=verified",
                self.camera_id,
                track_id,
                event_type,
            )
        return persisted_count
