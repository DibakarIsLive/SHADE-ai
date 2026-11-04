"""Run one configured video-file camera outside Django's HTTP lifecycle."""

from __future__ import annotations

import logging
import signal
import threading
from contextlib import contextmanager
from collections.abc import Iterator

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cameras.services import get_camera
from events.services import create_event
from monitoring.protocol import emit_lifecycle_event
from monitoring.worker import MonitoringWorker
from vision.providers import DevelopmentNullVisionProvider, RTMOVisionProvider
from vision.sources import VideoFileCameraSource, VideoSourceError


LOGGER = logging.getLogger(__name__)


def positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("must be a positive integer") from exc
    if parsed < 1:
        raise ValueError("must be a positive integer")
    return parsed


@contextmanager
def _shutdown_signal_handlers(stop_event: threading.Event) -> Iterator[None]:
    """Translate SIGINT/SIGTERM into a cooperative stop request."""
    previous_handlers: dict[int, object] = {}

    def request_shutdown(signum: int, _frame: object) -> None:
        try:
            signal_name = signal.Signals(signum).name
        except ValueError:
            signal_name = str(signum)
        LOGGER.info("monitor.shutdown_requested signal=%s", signal_name)
        stop_event.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            previous_handlers[signum] = signal.getsignal(signum)
            signal.signal(signum, request_shutdown)
        except ValueError:
            # Signal handlers can only be installed by Python's main thread.
            break

    try:
        yield
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


class Command(BaseCommand):
    help = "Run a standalone monitoring worker against one configured video file."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--camera-id",
            required=True,
            help="Identifier of an enabled video_file camera configuration.",
        )
        parser.add_argument(
            "--max-frames",
            type=positive_integer,
            help="Optional positive frame limit for a bounded development run.",
        )
        parser.add_argument(
            "--supervised",
            action="store_true",
            help="Emit lifecycle events for the Django worker supervisor.",
        )

    def _emit_lifecycle(self, options, event: str, **payload) -> None:
        if options.get("supervised"):
            emit_lifecycle_event(self.stdout, event, **payload)

    def _emit_failure(self, options, code: str) -> None:
        self._emit_lifecycle(options, "failed", code=code)

    def handle(self, *args, **options) -> None:
        camera_id = options["camera_id"]
        try:
            camera = get_camera(camera_id)
        except Exception as exc:
            LOGGER.exception(
                "monitor.camera_lookup_failure camera_id=%s error_type=%s",
                camera_id,
                type(exc).__name__,
            )
            self._emit_failure(options, "CAMERA_UNAVAILABLE")
            raise CommandError(
                "Camera configuration lookup failed; verify MongoDB availability and camera configuration."
            ) from exc

        if camera is None:
            self._emit_failure(options, "CAMERA_UNAVAILABLE")
            raise CommandError(f"Camera not found: {camera_id}")
        if not camera.enabled:
            self._emit_failure(options, "CAMERA_UNAVAILABLE")
            raise CommandError(f"Camera is disabled: {camera_id}")
        if camera.source_type != "video_file":
            self._emit_failure(options, "CAMERA_UNAVAILABLE")
            raise CommandError(
                f"Unsupported source type '{camera.source_type}'; run_monitor currently supports video_file only."
            )
        if not camera.source_uri:
            self._emit_failure(options, "CAMERA_UNAVAILABLE")
            raise CommandError("Video file source URI is missing from the camera configuration.")

        provider_name = getattr(settings, "VISION_PROVIDER", "development-null")
        if provider_name not in {"development-null", "rtmo-s"}:
            self._emit_failure(options, "INFERENCE_UNAVAILABLE")
            raise CommandError(f"Unsupported VISION_PROVIDER '{provider_name}'.")
        try:
            provider = (
                RTMOVisionProvider()
                if provider_name == "rtmo-s"
                else DevelopmentNullVisionProvider()
            )
            pipeline = provider.build_pipeline()
        except Exception as exc:
            LOGGER.exception(
                "monitor.provider_initialization_failed camera_id=%s provider=%s error_type=%s",
                camera_id,
                provider_name,
                type(exc).__name__,
            )
            self._emit_failure(options, "INFERENCE_UNAVAILABLE")
            raise CommandError(f"Vision provider initialization failed: {exc}") from exc

        model_name = str(getattr(provider, "model_name", "no-model"))
        LOGGER.info(
            "monitor.provider_ready camera_id=%s source_type=%s provider=%s model=%s device=%s confidence_threshold=%s",
            camera.camera_id,
            camera.source_type,
            provider.name,
            model_name,
            getattr(getattr(provider, "config", None), "device", "not-applicable"),
            getattr(getattr(provider, "config", None), "confidence_threshold", "not-applicable"),
        )
        self._emit_lifecycle(
            options,
            "provider_ready",
            provider=provider.name,
            model_name=model_name,
            inference_available=bool(provider.inference_available),
        )

        try:
            source = VideoFileCameraSource(
                source_uri=camera.source_uri,
                camera_id=camera.camera_id,
            )
        except VideoSourceError as exc:
            self._emit_failure(options, "CAMERA_UNAVAILABLE")
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            LOGGER.exception(
                "monitor.source_initialization_failed camera_id=%s error_type=%s",
                camera_id,
                type(exc).__name__,
            )
            self._emit_failure(options, "CAMERA_UNAVAILABLE")
            raise CommandError("Video-file source initialization failed.") from exc

        stop_event = threading.Event()
        worker = MonitoringWorker(
            source,
            pipeline,
            camera_id=camera.camera_id,
            camera_name=camera.name,
            provider_name=provider.name,
            model_name=model_name,
            model_version=getattr(provider, "model_version", None),
            artifact_sha256=getattr(provider, "artifact_sha256", None),
            source_type=camera.source_type,
            inference_available=provider.inference_available,
            event_persister=create_event,
            stop_event=stop_event,
            on_source_opened=lambda: self._emit_lifecycle(options, "source_ready"),
        )
        LOGGER.info(
            "monitor.camera_configuration_loaded camera_id=%s camera_name=%s source_type=%s source_name=%s enabled=%s",
            camera.camera_id,
            camera.name,
            camera.source_type,
            source.path.name,
            camera.enabled,
        )

        try:
            with _shutdown_signal_handlers(stop_event):
                processed = worker.run(max_frames=options["max_frames"])
        except VideoSourceError as exc:
            self._emit_failure(options, "CAMERA_UNAVAILABLE")
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            LOGGER.exception(
                "monitor.command_failure camera_id=%s error_type=%s",
                camera_id,
                type(exc).__name__,
            )
            self._emit_failure(options, "WORKER_FAILED")
            raise CommandError(f"Monitoring worker failed: {exc}") from exc

        self.stdout.write(
            f"Worker stopped after {processed} frame(s) from configured camera '{camera.name}' ({camera.camera_id})."
        )
        if not provider.inference_available:
            self.stdout.write(
                "Inference provider: development-null (unavailable); no detections or emergency events were generated."
            )
        else:
            self.stdout.write(
                f"Inference provider: {provider.name} (initialized: {model_name}); any verified event still requires the existing temporal checks."
            )
