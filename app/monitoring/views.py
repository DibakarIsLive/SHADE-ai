"""Monitoring control endpoints; camera work belongs to a worker boundary."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from monitoring.runtime import monitoring_controller
from monitoring.serializers import MonitoringStartSerializer


class MonitoringStatusView(APIView):
    def get(self, request):  # noqa: ARG002
        return Response(monitoring_controller.snapshot())


class MonitoringStartView(APIView):
    def post(self, request):
        serializer = MonitoringStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            monitoring_controller.start(serializer.validated_data["camera_id"]),
            status=status.HTTP_202_ACCEPTED,
        )


class MonitoringStopView(APIView):
    def post(self, request):  # noqa: ARG002
        return Response(monitoring_controller.stop(), status=status.HTTP_202_ACCEPTED)
