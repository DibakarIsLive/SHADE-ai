from __future__ import annotations

from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
import pytest

from monitoring.management.commands import run_monitor
from vision.providers import DevelopmentNullVisionProvider


@pytest.mark.parametrize(
    ("camera", "message"),
    [
        (None, "Camera not found"),
        (SimpleNamespace(camera_id="disabled", enabled=False), "Camera is disabled"),
        (
            SimpleNamespace(camera_id="webcam", enabled=True, source_type="webcam"),
            "currently supports video_file only",
        ),
        (
            SimpleNamespace(
                camera_id="missing-uri", enabled=True, source_type="video_file", source_uri=""
            ),
            "source URI is missing",
        ),
    ],
)
def test_command_rejects_invalid_camera_configuration(monkeypatch, camera, message):
    monkeypatch.setattr(run_monitor, "get_camera", lambda _camera_id: camera)

    with pytest.raises(CommandError, match=message):
        call_command("run_monitor", camera_id="configured-camera", stdout=StringIO())


def test_command_rejects_a_missing_configured_video_path(monkeypatch, tmp_path: Path):
    camera = SimpleNamespace(
        camera_id="configured-camera",
        name="Local file",
        enabled=True,
        source_type="video_file",
        source_uri=str(tmp_path / "missing.avi"),
    )
    monkeypatch.setattr(run_monitor, "get_camera", lambda _camera_id: camera)

    with pytest.raises(CommandError, match="Video file does not exist"):
        call_command("run_monitor", camera_id=camera.camera_id, stdout=StringIO())


def test_command_executes_video_pipeline_and_labels_null_inference(
    monkeypatch,
    tmp_path: Path,
):
    source = SimpleNamespace(path=tmp_path / "configured-video.avi")
    camera = SimpleNamespace(
        camera_id="configured-camera",
        name="Recorded test source",
        enabled=True,
        source_type="video_file",
        source_uri=str(source.path),
    )
    monkeypatch.setattr(run_monitor, "get_camera", lambda _camera_id: camera)
    monkeypatch.setattr(settings, "VISION_PROVIDER", "development-null")
    monkeypatch.setattr(
        run_monitor,
        "VideoFileCameraSource",
        lambda source_uri, camera_id: source,
    )

    class FakeWorker:
        def __init__(self, received_source, pipeline, **kwargs):
            assert received_source is source
            assert isinstance(pipeline, DevelopmentNullVisionProvider().build_pipeline().__class__)
            assert kwargs["camera_id"] == camera.camera_id
            assert kwargs["provider_name"] == "development-null"
            assert kwargs["source_type"] == "video_file"
            assert kwargs["inference_available"] is False

        def run(self, max_frames=None):
            assert max_frames == 3
            return 3

    monkeypatch.setattr(run_monitor, "MonitoringWorker", FakeWorker)
    output = StringIO()

    call_command(
        "run_monitor",
        camera_id=camera.camera_id,
        max_frames=3,
        stdout=output,
    )

    assert "stopped after 3 frame(s)" in output.getvalue()
    assert "development-null (unavailable)" in output.getvalue()
    assert "no detections or emergency events were generated" in output.getvalue()


def test_command_selects_configured_rtmo_provider_and_passes_provenance(
    monkeypatch, tmp_path: Path
):
    source = SimpleNamespace(path=tmp_path / "configured-video.avi")
    camera = SimpleNamespace(
        camera_id="configured-camera",
        name="Recorded test source",
        enabled=True,
        source_type="video_file",
        source_uri=str(source.path),
    )
    pipeline = object()
    monkeypatch.setattr(run_monitor, "get_camera", lambda _camera_id: camera)
    monkeypatch.setattr(settings, "VISION_PROVIDER", "rtmo-s")
    monkeypatch.setattr(
        run_monitor, "VideoFileCameraSource", lambda source_uri, camera_id: source
    )

    class FakeRTMOProvider:
        name = "mmpose-rtmo-s-body7-onnx"
        model_name = "RTMO-S body7 test artifact"
        model_version = None
        artifact_sha256 = "a" * 64
        inference_available = True
        config = SimpleNamespace(device="cpu", confidence_threshold=0.25)

        def build_pipeline(self):
            return pipeline

    class FakeWorker:
        def __init__(self, received_source, received_pipeline, **kwargs):
            assert received_source is source
            assert received_pipeline is pipeline
            assert kwargs["provider_name"] == FakeRTMOProvider.name
            assert kwargs["model_name"] == FakeRTMOProvider.model_name
            assert kwargs["model_version"] is None
            assert kwargs["artifact_sha256"] == "a" * 64
            assert kwargs["source_type"] == "video_file"
            assert kwargs["camera_id"] == camera.camera_id
            assert kwargs["camera_name"] == camera.name
            assert kwargs["inference_available"] is True

        def run(self, max_frames=None):
            assert max_frames is None
            return 2

    monkeypatch.setattr(run_monitor, "RTMOVisionProvider", FakeRTMOProvider)
    monkeypatch.setattr(run_monitor, "MonitoringWorker", FakeWorker)
    output = StringIO()

    call_command("run_monitor", camera_id=camera.camera_id, stdout=output)

    assert "mmpose-rtmo-s-body7-onnx" in output.getvalue()
    assert "RTMO-S body7 test artifact" in output.getvalue()
    assert "existing temporal checks" in output.getvalue()


def test_command_fails_before_opening_source_when_configured_model_is_missing(
    monkeypatch, tmp_path: Path
):
    camera = SimpleNamespace(
        camera_id="configured-camera",
        name="Recorded test source",
        enabled=True,
        source_type="video_file",
        source_uri=str(tmp_path / "missing.avi"),
    )
    source_constructed = []
    monkeypatch.setattr(run_monitor, "get_camera", lambda _camera_id: camera)
    monkeypatch.setattr(settings, "VISION_PROVIDER", "rtmo-s")
    monkeypatch.setattr(
        run_monitor,
        "VideoFileCameraSource",
        lambda **_kwargs: source_constructed.append(True),
    )

    class MissingModelProvider:
        name = "mmpose-rtmo-s-body7-onnx"
        model_name = "RTMO-S body7 test artifact"
        inference_available = False

        def build_pipeline(self):
            from vision.rtmo import RTMOConfigurationError

            raise RTMOConfigurationError("Vision model weights unavailable: model.onnx")

    monkeypatch.setattr(run_monitor, "RTMOVisionProvider", MissingModelProvider)

    with pytest.raises(CommandError, match="Vision model weights unavailable"):
        call_command("run_monitor", camera_id=camera.camera_id, stdout=StringIO())
    assert source_constructed == []


def test_command_rejects_unknown_configured_provider(monkeypatch, tmp_path: Path):
    camera = SimpleNamespace(
        camera_id="configured-camera",
        name="Recorded test source",
        enabled=True,
        source_type="video_file",
        source_uri=str(tmp_path / "configured-video.avi"),
    )
    monkeypatch.setattr(run_monitor, "get_camera", lambda _camera_id: camera)
    monkeypatch.setattr(settings, "VISION_PROVIDER", "unknown-provider")

    with pytest.raises(CommandError, match="Unsupported VISION_PROVIDER"):
        call_command("run_monitor", camera_id=camera.camera_id, stdout=StringIO())
