"""Camera source adapters used by the monitoring worker."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import datetime, timedelta, timezone

from vision.types import Frame


class SyntheticCameraSource:
    """Deterministic source for tests and safe dashboard demonstrations."""

    def __init__(self, frame_count: int = 1, width: int = 1280, height: int = 720) -> None:
        self.frame_count = frame_count
        self.width = width
        self.height = height
        self.closed = False

    def frames(self) -> Iterable[Frame]:
        start = datetime.now(timezone.utc)
        for frame_number in range(self.frame_count):
            yield Frame(
                frame_number=frame_number,
                captured_at=start + timedelta(milliseconds=100 * frame_number),
                payload=None,
                width=self.width,
                height=self.height,
            )

    def close(self) -> None:
        self.closed = True


class IterableFrameSource:
    """Wrap an existing frame iterable for focused pipeline tests."""

    def __init__(self, frames: Iterable[Frame]) -> None:
        self._frames = frames
        self.closed = False

    def frames(self) -> Iterator[Frame]:
        yield from self._frames

    def close(self) -> None:
        self.closed = True
