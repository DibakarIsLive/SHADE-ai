"""Camera source adapters used by the monitoring worker."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable, Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import cv2

from vision.types import Frame


class VideoSourceError(RuntimeError):
    """A video-file source is invalid, unreadable, or cannot be released."""


class SyntheticCameraSource:
    """Deterministic frame-less source for tests; it never represents a camera."""

    def __init__(self, frame_count: int = 1, width: int = 1280, height: int = 720) -> None:
        if frame_count < 0:
            raise ValueError("frame_count must not be negative")
        self.frame_count = frame_count
        self.width: int | None = width
        self.height: int | None = height
        self.fps: float | None = 10.0
        self.closed = False
        self.end_of_stream = False
        self._opened = False

    @property
    def is_opened(self) -> bool:
        return self._opened and not self.closed

    def open(self) -> None:
        if self.closed:
            raise RuntimeError("A closed synthetic source cannot be reopened.")
        self._opened = True

    def frames(self) -> Iterable[Frame]:
        self.open()
        start = datetime.now(timezone.utc)
        for frame_number in range(self.frame_count):
            yield Frame(
                frame_number=frame_number,
                captured_at=start + timedelta(milliseconds=100 * frame_number),
                payload=None,
                width=self.width or 0,
                height=self.height or 0,
            )
        self.end_of_stream = True

    def close(self) -> None:
        self.closed = True
        self._opened = False


class IterableFrameSource:
    """Wrap an existing frame iterable for focused pipeline tests."""

    def __init__(self, frames: Iterable[Frame]) -> None:
        self._frames = frames
        self.closed = False
        self.end_of_stream = False
        self.width: int | None = None
        self.height: int | None = None
        self.fps: float | None = None
        self._opened = False

    @property
    def is_opened(self) -> bool:
        return self._opened and not self.closed

    def open(self) -> None:
        if self.closed:
            raise RuntimeError("A closed iterable source cannot be reopened.")
        self._opened = True

    def frames(self) -> Iterator[Frame]:
        self.open()
        for frame in self._frames:
            self.width = frame.width or None
            self.height = frame.height or None
            yield frame
        self.end_of_stream = True

    def close(self) -> None:
        self.closed = True
        self._opened = False


class VideoFileCameraSource:
    """Read a local video file sequentially without silently looping it."""

    def __init__(
        self,
        source_uri: str,
        camera_id: str = "",
        *,
        capture_factory: Callable[[str], Any] | None = None,
    ) -> None:
        normalized_uri = source_uri.strip() if isinstance(source_uri, str) else ""
        if not normalized_uri:
            raise VideoSourceError("A source_uri is required for a video-file camera.")

        configured_path = Path(normalized_uri).expanduser()
        self._display_name = configured_path.name or "<unnamed video file>"
        if not configured_path.is_file():
            raise VideoSourceError(
                f"Video file does not exist or is not a regular file: {self._display_name}"
            )

        self.path = configured_path.resolve()
        self.camera_id = camera_id
        self._capture_factory = capture_factory or cv2.VideoCapture
        self._capture: Any | None = None
        self._closed = False
        self.end_of_stream = False
        self.frames_read = 0
        self.width: int | None = None
        self.height: int | None = None
        self.fps: float | None = None
        self._timeline_started_at: datetime | None = None

    @property
    def is_opened(self) -> bool:
        if self._capture is None or self._closed:
            return False
        try:
            return bool(self._capture.isOpened())
        except Exception:
            return False

    def open(self) -> None:
        """Open the configured file once and capture available metadata."""
        if self._closed:
            raise VideoSourceError("A closed video source cannot be reopened.")
        if self.is_opened:
            return
        if not self.path.is_file():
            raise VideoSourceError(
                f"Video file does not exist or is not a regular file: {self._display_name}"
            )

        try:
            capture = self._capture_factory(str(self.path))
        except Exception as exc:
            raise VideoSourceError(
                f"Video source could not be opened: {self._display_name}"
            ) from exc

        self._capture = capture
        try:
            if not bool(capture.isOpened()):
                self._release_capture()
                raise VideoSourceError(
                    f"Video source could not be opened: {self._display_name}"
                )
            self.width = self._positive_int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height = self._positive_int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.fps = self._positive_float(capture.get(cv2.CAP_PROP_FPS))
            self._timeline_started_at = datetime.now(timezone.utc)
        except VideoSourceError:
            raise
        except Exception as exc:
            self._release_capture()
            raise VideoSourceError(
                f"Video source metadata could not be read: {self._display_name}"
            ) from exc

    def frames(self) -> Iterator[Frame]:
        """Yield decoded frames in file order and stop at end-of-stream."""
        if self.end_of_stream:
            return
        self.open()
        if self._capture is None:
            raise VideoSourceError(f"Video source is not open: {self._display_name}")

        while True:
            try:
                success, image = self._capture.read()
            except Exception as exc:
                raise VideoSourceError(
                    f"Video source failed while reading: {self._display_name}"
                ) from exc

            if not success:
                self.end_of_stream = True
                if self.frames_read == 0:
                    raise VideoSourceError(
                        f"Video source opened but contains no readable frames: {self._display_name}"
                    )
                return
            if image is None or getattr(image, "ndim", 0) < 2:
                raise VideoSourceError(
                    f"Video source returned an invalid frame: {self._display_name}"
                )

            height, width = image.shape[:2]
            if width < 1 or height < 1:
                raise VideoSourceError(
                    f"Video source returned an empty frame: {self._display_name}"
                )
            self.width = int(width)
            self.height = int(height)
            if self.fps is not None and self._timeline_started_at is not None:
                captured_at = self._timeline_started_at + timedelta(
                    seconds=self.frames_read / self.fps
                )
            else:
                captured_at = datetime.now(timezone.utc)

            frame_number = self.frames_read
            self.frames_read += 1
            yield Frame(
                frame_number=frame_number,
                captured_at=captured_at,
                payload=image,
                width=self.width,
                height=self.height,
            )

    def close(self) -> None:
        """Release the decoder; repeated calls are safe."""
        self._closed = True
        try:
            self._release_capture()
        except Exception as exc:
            raise VideoSourceError(
                f"Video source could not be released: {self._display_name}"
            ) from exc

    def _release_capture(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            capture.release()

    @staticmethod
    def _positive_int(value: Any) -> int | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return int(number) if math.isfinite(number) and number > 0 else None

    @staticmethod
    def _positive_float(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) and number > 0 else None
