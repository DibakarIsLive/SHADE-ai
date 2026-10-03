from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest

from vision.sources import VideoFileCameraSource, VideoSourceError


@pytest.fixture
def small_video_file(tmp_path: Path) -> Path:
    path = tmp_path / "repeatable-video.avi"
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10.0,
        (32, 24),
    )
    if not writer.isOpened():
        writer.release()
        pytest.skip("This OpenCV build has no working MJPG VideoWriter backend.")
    try:
        for index in range(4):
            frame = np.zeros((24, 32, 3), dtype=np.uint8)
            frame[:, :, 0] = index * 40
            frame[:, :, 1] = 100
            writer.write(frame)
    finally:
        writer.release()
    assert path.is_file()
    return path


def test_video_source_requires_a_configured_file(tmp_path: Path):
    with pytest.raises(VideoSourceError, match="source_uri is required"):
        VideoFileCameraSource("")

    with pytest.raises(VideoSourceError, match="does not exist"):
        VideoFileCameraSource(str(tmp_path / "missing.avi"))


def test_video_source_reports_an_existing_but_unopenable_file(tmp_path: Path):
    path = tmp_path / "not-a-video.avi"
    path.write_bytes(b"not a video")

    class FailedCapture:
        released = False

        def isOpened(self) -> bool:
            return False

        def release(self) -> None:
            self.released = True

    capture = FailedCapture()
    source = VideoFileCameraSource(str(path), capture_factory=lambda _path: capture)

    with pytest.raises(VideoSourceError, match="Video source could not be opened"):
        source.open()

    assert capture.released is True
    assert source.is_opened is False


def test_video_source_reports_decoder_construction_failure(tmp_path: Path):
    path = tmp_path / "placeholder.avi"
    path.write_bytes(b"present")

    def fail_to_construct(_path: str) -> Any:
        raise OSError("decoder unavailable")

    source = VideoFileCameraSource(str(path), capture_factory=fail_to_construct)

    with pytest.raises(VideoSourceError, match="Video source could not be opened"):
        source.open()


def test_video_source_opens_reads_sequential_frames_and_stops_at_eof(small_video_file: Path):
    source = VideoFileCameraSource(str(small_video_file), camera_id="video-fixture")

    source.open()
    assert source.is_opened is True
    assert (source.width, source.height, source.fps) == (32, 24, 10.0)

    frames = list(source.frames())

    assert [frame.frame_number for frame in frames] == [0, 1, 2, 3]
    assert all(frame.payload.shape == (24, 32, 3) for frame in frames)
    assert all(frame.width == 32 and frame.height == 24 for frame in frames)
    assert frames[0].captured_at < frames[1].captured_at < frames[2].captured_at
    assert source.frames_read == 4
    assert source.end_of_stream is True
    assert list(source.frames()) == []

    source.close()
    source.close()
    assert source.is_opened is False


def test_video_source_closes_when_frame_iteration_is_abandoned(small_video_file: Path):
    source = VideoFileCameraSource(str(small_video_file))
    iterator = source.frames()

    first = next(iterator)

    assert first.frame_number == 0
    assert source.is_opened is True
    source.close()
    iterator.close()
    assert source.is_opened is False


def test_empty_video_is_not_reported_as_a_successful_empty_stream(tmp_path: Path):
    path = tmp_path / "empty-video.avi"
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (32, 24)
    )
    if not writer.isOpened():
        writer.release()
        pytest.skip("This OpenCV build has no working MJPG VideoWriter backend.")
    writer.release()

    source = VideoFileCameraSource(str(path))
    try:
        with pytest.raises(VideoSourceError, match="no readable frames"):
            list(source.frames())
    finally:
        source.close()
