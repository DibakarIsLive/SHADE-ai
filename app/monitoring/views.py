"""Monitoring control endpoints backed by the real local worker supervisor."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from cameras.services import get_camera
from monitoring.serializers import MonitoringStartSerializer
from monitoring.supervisor import (
    WorkerConflictError,
    WorkerStoppingError,
    worker_supervisor,
)


LOGGER = logging.getLogger(__name__)


class MonitoringStatusView(APIView):
    def get(self, request):  # noqa: ARG002
        response = Response(worker_supervisor.snapshot())
        response["Cache-Control"] = "no-store"
        return response


class MonitoringStartView(APIView):
    def post(self, request):
        serializer = MonitoringStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        camera_id = serializer.validated_data["camera_id"]
        try:
            camera = get_camera(camera_id)
        except Exception:
            LOGGER.exception("monitor.camera_validation_unavailable camera_id=%s", camera_id)
            return Response(
                {"detail": "Camera configuration could not be verified because persistence is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if camera is None:
            return Response({"detail": "The requested camera configuration was not found."}, status=404)
        if not camera.enabled:
            return Response({"detail": "The requested camera is disabled."}, status=400)
        if camera.source_type != "video_file":
            return Response(
                {"detail": "Monitoring currently supports enabled video_file camera configurations only."},
                status=400,
            )
        if not isinstance(camera.source_uri, str) or not camera.source_uri.strip():
            return Response({"detail": "The configured video-file source URI is missing."}, status=400)

        try:
            snapshot, launched = worker_supervisor.start(camera_id)
        except WorkerStoppingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except WorkerConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except RuntimeError:
            LOGGER.exception("monitor.supervisor_unavailable")
            return Response(
                {"detail": "The local monitoring supervisor is shutting down."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(snapshot, status=status.HTTP_202_ACCEPTED if launched else status.HTTP_200_OK)


class MonitoringStopView(APIView):
    def post(self, request):  # noqa: ARG002
        snapshot = worker_supervisor.stop()
        response_status = status.HTTP_202_ACCEPTED if snapshot["status"] == "STOPPING" else status.HTTP_200_OK
        return Response(snapshot, status=response_status)
