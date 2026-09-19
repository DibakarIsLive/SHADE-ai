"""HTTP endpoints for verified monitoring events."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from events.serializers import EventCreateSerializer
from events.services import create_event, list_events


LOGGER = logging.getLogger(__name__)


class EventListCreateView(APIView):
    def get(self, request):  # noqa: ARG002
        try:
            items = list_events()
        except Exception as exc:
            LOGGER.warning("Could not list emergency events: %s", exc)
            return Response(
                {
                    "items": [],
                    "count": 0,
                    "persistence": "unavailable",
                    "detail": "MongoDB is unavailable; event history cannot be listed yet.",
                }
            )
        return Response({"items": items, "count": len(items), "persistence": "available"})

    def post(self, request):
        serializer = EventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            event = create_event(serializer.validated_data)
        except Exception as exc:
            LOGGER.warning("Could not create emergency event: %s", exc)
            return Response(
                {
                    "detail": "MongoDB is unavailable; event was not saved.",
                    "persistence": "unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(event, status=status.HTTP_201_CREATED)
