"""Worker boundary for camera processing.

The API must not capture frames or run inference inside request handlers. A later
management command or process supervisor will instantiate this worker with a
CameraSource, detector, tracker, posture analyzer, and temporal engine.
"""

from __future__ import annotations

import logging

from vision.pipeline import VisionPipeline
from vision.sources import CameraSource


LOGGER = logging.getLogger(__name__)


class MonitoringWorker:
    """Coordinate frame processing outside the HTTP request lifecycle."""

    def __init__(self, source: CameraSource, pipeline: VisionPipeline) -> None:
        self.source = source
        self.pipeline = pipeline
        self.running = False

    def run(self, max_frames: int | None = None) -> int:
        """Process frames until the source ends or an optional limit is reached."""
        self.running = True
        processed = 0
        try:
            for frame in self.source.frames():
                if max_frames is not None and processed >= max_frames:
                    break
                self.pipeline.process(frame)
                processed += 1
        finally:
            self.running = False
            self.source.close()
        LOGGER.info("Monitoring worker processed %s frames", processed)
        return processed
