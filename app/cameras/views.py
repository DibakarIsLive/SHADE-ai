"""HTTP endpoints for configured camera sources."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from cameras.serializers import CameraCreateSerializer
from cameras.services import create_camera, list_cameras


LOGGER = logging.getLogger(__name__)


class CameraListCreateView(APIView):
    def get(self, request):  # noqa: ARG002
        try:
            items = list_cameras()
        except Exception as exc:  # MongoDB may be offline during local exploration.
            LOGGER.warning("Could not list cameras: %s", exc)
            return Response(
                {
                    "items": [],
                    "count": 0,
                    "persistence": "unavailable",
                    "detail": "MongoDB is unavailable; camera records cannot be listed yet.",
                }
            )
        return Response({"items": items, "count": len(items), "persistence": "available"})

    def post(self, request):
        serializer = CameraCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            camera = create_camera(serializer.validated_data)
        except Exception as exc:
            LOGGER.warning("Could not create camera: %s", exc)
            return Response(
                {
                    "detail": "MongoDB is unavailable; camera registration was not saved.",
                    "persistence": "unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(camera, status=status.HTTP_201_CREATED)
