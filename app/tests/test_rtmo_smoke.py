"""Opt-in real RTMO-S CPU smoke test; never downloads weights or media."""

from __future__ import annotations

import os
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from django.conf import settings

from vision.providers import RTMOVisionProvider
from vision.sources import VideoFileCameraSource


@pytest.mark.model_smoke
def test_real_cpu_model_processes_video_into_normalized_observations(tmp_path: Path):
    """Exercise local video decoding, ONNX inference, and SHADE observation mapping."""
    if os.environ.get("VISION_MODEL_SMOKE") != "1":
        pytest.skip("Set VISION_MODEL_SMOKE=1 to opt in to real model execution.")

    model_path = Path(settings.VISION_MODEL_PATH).expanduser()
    if not model_path.is_file():
        pytest.skip(
            "RTMO-S weights are not provisioned; set VISION_MODEL_PATH to a local ONNX artifact."
        )

    image_setting = os.environ.get("VISION_MODEL_SMOKE_IMAGE", "").strip()
    if not image_setting:
        pytest.skip(
            "Set VISION_MODEL_SMOKE_IMAGE to a locally available, appropriately licensed person image."
        )
    image_path = Path(image_setting).expanduser()
    if not image_path.is_file():
        pytest.skip("The configured VISION_MODEL_SMOKE_IMAGE file is unavailable.")
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None or image.ndim != 3 or image.shape[2] != 3 or image.size == 0:
        pytest.fail("The configured smoke image is not a readable color image.")

    # Encode three copies into a temporary, locally decoded clip. This establishes the
    # real video-file → CPU model → neutral observation path, not a temporal fall sequence.
    width, height = 960, 640
    resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    video_path = tmp_path / "rtmo-smoke.avi"
    writer = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 5.0, (width, height)
    )
    if not writer.isOpened():
        writer.release()
        pytest.skip("This OpenCV build has no working MJPG VideoWriter backend.")
    try:
        for _ in range(3):
            writer.write(resized)
    finally:
        writer.release()

    provider = RTMOVisionProvider(
        model_path=model_path,
        device="cpu",
        confidence_threshold=settings.VISION_CONFIDENCE_THRESHOLD,
        keypoint_threshold=settings.VISION_KEYPOINT_THRESHOLD,
    )
    initialization_started = time.perf_counter()
    pipeline = provider.build_pipeline()
    initialization_seconds = time.perf_counter() - initialization_started
    assert provider.inference_available is True

    source = VideoFileCameraSource(str(video_path), camera_id="rtmo-smoke")
    inference_seconds: list[float] = []
    frame_count = 0
    observation_count = 0
    decision_count = 0
    first_observation = None
    try:
        source.open()
        for video_frame in source.frames():
            inference_started = time.perf_counter()
            result = pipeline.process(video_frame)
            inference_seconds.append(time.perf_counter() - inference_started)
            frame_count += 1
            observation_count += len(result.observations)
            decision_count += len(result.decisions)
            if first_observation is None and result.observations:
                first_observation = result.observations[0]
    finally:
        source.close()

    assert frame_count == 3, "The temporary smoke clip must be decoded in full."
    assert first_observation is not None, (
        "The real model emitted no person observations for the supplied smoke image; "
        "use a representative, appropriately licensed local image."
    )
    assert first_observation.track_id.startswith("local-track-")
    assert first_observation.pose.keypoints, "Expected normalized pose keypoints from RTMO-S."
    assert first_observation.metadata["vision_provider"] == provider.name
    assert first_observation.metadata["model"] == provider.model_name
    assert first_observation.metadata["observation_type"] == "pose_heuristic_not_activity_model"
    assert 0.0 <= first_observation.metadata["model_confidence"] <= 1.0
    assert decision_count == observation_count

    mean_inference_seconds = sum(inference_seconds) / len(inference_seconds)
    print(
        "REAL_MODEL_SMOKE "
        f"provider={provider.name} model={provider.model_name!r} device=cpu "
        f"artifact={model_path.name!r} source=video_file image={image_path.name!r} "
        f"resolution={width}x{height} frames={frame_count} observations={observation_count} "
        f"initialization_seconds={initialization_seconds:.3f} "
        f"mean_pipeline_seconds_per_frame={mean_inference_seconds:.3f} "
        f"measured_pipeline_fps={1.0 / mean_inference_seconds:.3f} "
        "fall_event_demonstrated=false model_backed_mongodb_event_demonstrated=false"
    )
