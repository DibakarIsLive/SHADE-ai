from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from vision.pipeline import VisionPipeline
from vision.providers import RTMOVisionProvider
from vision.rtmo import (
    KEYPOINT_NAMES,
    RTMOAdapter,
    RTMOConfig,
    RTMOConfigurationError,
    RTMOInferenceError,
)
from vision.tracking import IoUPersonTracker
from vision.types import BoundingBox, Detection, Frame, Track


class FakeSession:
    def __init__(self, detections, keypoints):
        self.detections = np.asarray(detections, dtype=np.float32)
        self.keypoints = np.asarray(keypoints, dtype=np.float32)
        self.calls = 0
        self.feed = None

    def get_inputs(self):
        return [SimpleNamespace(name="input")]

    def get_outputs(self):
        return [SimpleNamespace(name="dets"), SimpleNamespace(name="keypoints")]

    def run(self, names, feed):  # noqa: ARG002
        self.calls += 1
        self.feed = feed["input"]
        return [self.detections, self.keypoints]


def sample_keypoints(count=1):
    result = np.zeros((count, 17, 3), dtype=np.float32)
    for row in range(count):
        result[row, :, 0] = 320 + row * 30
        result[row, :, 1] = 320
        result[row, :, 2] = 0.9
    result[:, 5, :2] = np.array([320, 180], dtype=np.float32)
    result[:, 6, :2] = np.array([340, 180], dtype=np.float32)
    result[:, 11, :2] = np.array([320, 360], dtype=np.float32)
    result[:, 12, :2] = np.array([340, 360], dtype=np.float32)
    return result


def frame(number=0, width=640, height=640, payload=None):
    pixels = payload if payload is not None else np.full((height, width, 3), 64, np.uint8)
    return Frame(
        frame_number=number,
        captured_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        payload=pixels,
        width=width,
        height=height,
    )


def config(path, **kwargs):
    return RTMOConfig(model_path=Path(path), **kwargs)


def test_config_accepts_explicit_cpu_artifact_and_thresholds(tmp_path):
    model_path = tmp_path / "model.onnx"
    model_path.touch()
    result = config(
        model_path,
        confidence_threshold=0.4,
        keypoint_threshold=0.65,
    )

    assert result.device == "cpu"
    assert result.confidence_threshold == 0.4
    assert result.keypoint_threshold == 0.65
    assert result.model_path == model_path


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"device": "tpu"}, "VISION_DEVICE"),
        ({"confidence_threshold": float("nan")}, "VISION_CONFIDENCE_THRESHOLD"),
        ({"keypoint_threshold": 1.1}, "VISION_KEYPOINT_THRESHOLD"),
        ({"input_size": 320}, "640x640"),
    ],
)
def test_config_rejects_invalid_device_or_threshold(tmp_path, kwargs, message):
    model_path = tmp_path / "model.onnx"
    model_path.touch()
    with pytest.raises(RTMOConfigurationError, match=message):
        config(model_path, **kwargs)


def test_missing_weights_fail_truthfully_without_fallback(tmp_path):
    provider = RTMOVisionProvider(model_path=tmp_path / "missing.onnx", device="cpu")

    assert provider.inference_available is False
    with pytest.raises(RTMOConfigurationError, match="Vision model weights unavailable"):
        provider.build_pipeline()
    assert provider.inference_available is False


def test_provider_initializes_one_cpu_session_and_hashes_artifact_once(tmp_path, monkeypatch):
    import hashlib

    path = tmp_path / "model.onnx"
    path.write_bytes(b"stable-model-artifact")
    session = FakeSession(np.empty((1, 0, 5)), np.empty((1, 0, 17, 3)))
    provider = RTMOVisionProvider(model_path=path, device="cpu")
    provider.adapter._session_factory = lambda _path, providers: (  # noqa: ARG005
        session if providers == ["CPUExecutionProvider"] else pytest.fail("CPU provider not selected")
    )
    original_hash = provider.adapter._compute_artifact_sha256
    hash_calls = []

    def counted_hash(artifact_path):
        hash_calls.append(artifact_path)
        return original_hash(artifact_path)

    monkeypatch.setattr(provider.adapter, "_compute_artifact_sha256", counted_hash)
    expected_digest = hashlib.sha256(b"stable-model-artifact").hexdigest()

    pipeline = provider.build_pipeline()

    assert isinstance(pipeline, VisionPipeline)
    assert isinstance(provider.adapter.tracks, IoUPersonTracker)
    assert provider.inference_available is True
    assert provider.model_version is None
    assert provider.model_name == "RTMO-S body7 640x640 (MMPose ONNX export)"
    assert provider.artifact_sha256 == expected_digest
    assert hash_calls == [path]
    assert provider.build_pipeline().__class__ is VisionPipeline
    assert provider.artifact_sha256 == expected_digest
    assert hash_calls == [path]
    assert provider.inference_available is True


def test_initialization_rejects_unsupported_gpu_even_with_artifact(tmp_path):
    path = tmp_path / "model.onnx"
    path.touch()
    provider = RTMOVisionProvider(model_path=path, device="gpu")

    with pytest.raises(RTMOConfigurationError, match="CPU-only"):
        provider.build_pipeline()
    assert provider.inference_available is False


def test_initialization_rejects_an_incompatible_model_signature(tmp_path):
    path = tmp_path / "model.onnx"
    path.touch()

    class WrongSignature(FakeSession):
        def get_inputs(self):
            return [SimpleNamespace(name="images")]

    provider = RTMOVisionProvider(model_path=path, device="cpu")
    provider.adapter._session_factory = lambda *_args, **_kwargs: WrongSignature([], [])

    with pytest.raises(RTMOConfigurationError, match="input signature"):
        provider.build_pipeline()
    assert provider.inference_available is False


def test_missing_onnx_runtime_dependency_fails_truthfully(tmp_path, monkeypatch):
    path = tmp_path / "model.onnx"
    path.touch()
    adapter = RTMOAdapter(config(path))
    original_import = __import__

    def missing_runtime(name, *args, **kwargs):
        if name == "onnxruntime":
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", missing_runtime)
    with pytest.raises(RTMOConfigurationError, match="ONNX Runtime is unavailable"):
        adapter.initialize()


def test_normalizes_one_person_box_confidence_and_keypoints():
    raw_detections = np.array([[[100, 120, 500, 580, 0.91]]], dtype=np.float32)
    raw_keypoints = sample_keypoints()[None, ...]

    detections, poses = RTMOAdapter.normalize_outputs(
        raw_detections,
        raw_keypoints,
        frame_width=640,
        frame_height=640,
    )

    assert len(detections) == len(poses) == 1
    assert detections[0].label == "person"
    assert detections[0].confidence == pytest.approx(0.91)
    assert detections[0].bounding_box == BoundingBox(100, 120, 500, 580)
    assert set(poses[0].keypoints) == set(KEYPOINT_NAMES)
    assert poses[0].keypoint_confidences["nose"] == pytest.approx(0.9)
    assert poses[0].posture == "standing"


def test_normalizes_multiple_people_and_keeps_each_pose_available(tmp_path):
    detections = np.array(
        [[[80, 80, 240, 560, 0.9], [380, 80, 560, 570, 0.8]]],
        dtype=np.float32,
    )
    session = FakeSession(detections, sample_keypoints(2)[None, ...])
    path = tmp_path / "model.onnx"
    path.touch()
    adapter = RTMOAdapter(config(path), session_factory=lambda *_a, **_k: session)
    adapter.initialize()
    pipeline = VisionPipeline(
        detector=adapter,
        tracker=_PipelineTracker(adapter),
        pose_estimator=_PipelineStages(adapter, "pose"),
        classifier=_PipelineStages(adapter, "classifier"),
        verifier=_NeverVerify(),
    )
    result = pipeline.process(frame())

    assert len(result.observations) == 2
    assert all(item.pose.keypoints for item in result.observations)
    assert len({item.track_id for item in result.observations}) == 2
    assert session.calls == 1


class _PipelineTracker:
    def __init__(self, adapter):
        self.tracker = IoUPersonTracker()

    @property
    def retained_track_ids(self):
        return self.tracker.retained_track_ids

    def update(self, detections, frame):
        return self.tracker.update(detections, frame)


class _PipelineStages:
    def __init__(self, adapter, stage):
        self.adapter = adapter
        self.stage = stage

    def estimate(self, frame, track):
        return self.adapter.pose_for(frame, track)

    def classify(self, track, pose, frame):
        return self.adapter.classify(track, pose, frame)


class _NeverVerify:
    def observe(self, observation):  # noqa: ARG002
        from vision.types import VerificationDecision

        return VerificationDecision(False, None, 0.0, "not a fall", 1, 0.0)

    def retain_track_ids(self, track_ids):  # noqa: ARG002
        pass


def test_empty_model_output_has_no_detections_and_does_not_reuse_old_pose(tmp_path):
    outputs = [
        (np.array([[[100, 100, 500, 500, 0.9]]], np.float32), sample_keypoints()[None, ...]),
        (np.empty((1, 0, 5), np.float32), np.empty((1, 0, 17, 3), np.float32)),
    ]

    class SequentialSession(FakeSession):
        def run(self, names, feed):  # noqa: ARG002
            self.calls += 1
            return outputs.pop(0)

    path = tmp_path / "model.onnx"
    path.touch()
    session = SequentialSession([], [])
    adapter = RTMOAdapter(config(path), session_factory=lambda *_a, **_k: session)
    adapter.initialize()
    first, second = frame(0), frame(1)

    first_detections = adapter.detect(first)
    assert len(first_detections) == 1
    track = Track("worker-track", first_detections[0])
    adapter.detect(second)
    assert adapter._pending_poses == {}
    with pytest.raises(RTMOInferenceError, match="unavailable"):
        adapter.pose_for(second, track)


def test_low_confidence_detection_and_keypoints_are_omitted_not_relabelled():
    detections, poses = RTMOAdapter.normalize_outputs(
        np.array([[10, 10, 100, 200, 0.1]], dtype=np.float32),
        sample_keypoints(),
        frame_width=640,
        frame_height=640,
        confidence_threshold=0.25,
    )
    assert detections == poses == []

    keypoints = sample_keypoints()
    keypoints[0, 0, 2] = 0.05
    detections, poses = RTMOAdapter.normalize_outputs(
        np.array([[10, 10, 100, 200, 0.8]], dtype=np.float32),
        keypoints,
        frame_width=640,
        frame_height=640,
        keypoint_threshold=0.2,
    )
    assert len(detections) == len(poses) == 1
    assert "nose" not in poses[0].keypoints


@pytest.mark.parametrize(
    ("dets", "keypoints", "message"),
    [
        (np.zeros((1, 4), np.float32), np.zeros((1, 17, 3), np.float32), "shape"),
        (np.zeros((1, 5), np.float32), np.zeros((2, 17, 3), np.float32), "incompatible"),
        (np.array([[0, 0, 1, 1, 1.2]], np.float32), sample_keypoints(), "person confidence"),
        (np.array([[2, 2, 1, 3, 0.9]], np.float32), sample_keypoints(), "inverted"),
        (np.array([[0, 0, 10, 10, 0.9]], np.float32), np.full((1, 17, 3), np.nan), "non-finite"),
        (np.array([[0, 0, 10, 10, 0.9]], np.float32), sample_keypoints() * [1, 1, 2], "keypoint confidence"),
    ],
)
def test_malformed_model_outputs_are_rejected(dets, keypoints, message):
    with pytest.raises(RTMOInferenceError, match=message):
        RTMOAdapter.normalize_outputs(
            dets,
            keypoints,
            frame_width=640,
            frame_height=640,
        )


def test_affine_preprocessing_preserves_mmpose_fit_coordinates_and_pad():
    image = np.full((360, 640, 3), 64, dtype=np.uint8)
    image[0, 0] = [10, 20, 30]
    padded, matrix = RTMOAdapter._preprocess(image)
    inverse = cv2.invertAffineTransform(matrix)

    assert padded.shape == (640, 640, 3)
    assert np.allclose(matrix @ np.array([320, 180, 1]), [320, 320], atol=1e-4)
    assert np.allclose(inverse @ np.array([320, 320, 1]), [320, 180], atol=1e-4)
    assert tuple(padded[0, 0]) == (114, 114, 114)
    assert padded[320, 320].tolist() == [64, 64, 64]


def test_affine_preprocessing_handles_odd_portrait_and_landscape_frames():
    for width, height in ((321, 241), (241, 321), (641, 479), (479, 641)):
        image = np.arange(width * height * 3, dtype=np.uint32).reshape(height, width, 3)
        image = (image % 256).astype(np.uint8)
        padded, matrix = RTMOAdapter._preprocess(image)
        center = np.array([width / 2, height / 2, 1], dtype=np.float32)
        output_center = matrix @ center
        inverse = cv2.invertAffineTransform(matrix)
        restored = inverse @ np.append(output_center, 1.0)
        assert padded.shape == (640, 640, 3)
        assert np.allclose(output_center, [320, 320], atol=1e-4)
        assert np.allclose(restored, [width / 2, height / 2], atol=1e-4)
        assert np.isfinite(padded).all()


def test_frame_validation_rejects_inconsistent_dimensions_and_malformed_pixels():
    path = Path("unused.onnx")
    adapter = RTMOAdapter(config(path))
    with pytest.raises(RTMOInferenceError, match="inconsistent"):
        adapter._validate_frame(frame(width=639, height=480, payload=np.zeros((480, 640, 3), np.uint8)))
    with pytest.raises(RTMOInferenceError, match="uint8"):
        adapter._validate_frame(frame(payload=np.zeros((640, 640, 3), np.float32)))


def test_tracker_ages_dropped_detections_without_emitting_or_inventing_identity():
    tracker = IoUPersonTracker(max_missed_frames=1)
    person = Detection("person", 0.9, BoundingBox(10, 10, 20, 30))
    first = tracker.update([person], frame(0, width=40, height=50))
    assert len(first) == 1
    local_track_id = first[0].track_id
    assert local_track_id.startswith("local-track-")
    assert tracker.active_tracks[0].track_id == local_track_id

    assert tracker.update([], frame(1, width=40, height=50)) == []
    assert tracker.active_tracks == ()
    assert tracker.update([person], frame(2, width=40, height=50))[0].track_id == local_track_id
    assert tracker.update([], frame(3, width=40, height=50)) == []
    assert tracker.update([], frame(4, width=40, height=50)) == []
    assert tracker.active_tracks == ()
    assert tracker.update([person], frame(5, width=40, height=50))[0].track_id != local_track_id


def test_gpu_configuration_is_explicit_but_not_silently_substituted(tmp_path):
    path = tmp_path / "model.onnx"
    path.touch()
    provider = RTMOVisionProvider(model_path=path, device="gpu")
    with pytest.raises(RTMOConfigurationError, match="CPU-only"):
        provider.build_pipeline()
