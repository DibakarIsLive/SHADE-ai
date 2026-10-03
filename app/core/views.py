"""Small, dependency-light API metadata endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from config.database import check_mongodb
from monitoring.runtime import monitoring_controller


ACTIVITY_CATEGORIES = [
    "standing",
    "walking",
    "sitting",
    "running",
    "lying",
    "falling",
    "motionless",
]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class ApiRootView(APIView):
    """Describe the available HTTP resources without coupling to a database."""

    def get(self, request):  # noqa: ARG002
        return Response(
            {
                "service": "shade-ai-api",
                "name": "SHADE-ai",
                "version": "0.1.0",
                "status": "online",
                "principle": "observe-analyze-verify-respond",
                "links": {
                    "health": "/api/health/",
                    "capabilities": "/api/capabilities/",
                    "cameras": "/api/cameras/",
                    "events": "/api/events/",
                    "monitoring": "/api/monitoring/status/",
                    "monitoring_socket": "/ws/monitoring/",
                },
            }
        )


class HealthView(APIView):
    """Return bounded service and persistence diagnostics."""

    def get(self, request):  # noqa: ARG002
        database = check_mongodb()
        status = "healthy" if database["available"] else "degraded"
        return Response(
            {
                "service": "shade-ai-api",
                "status": status,
                "timestamp": utc_timestamp(),
                "database": database,
                "monitoring": monitoring_controller.snapshot(),
                "runtime": {
                    "mode": settings.MONITORING_MODE,
                    "vision_device": settings.VISION_DEVICE,
                    "notifications": settings.NOTIFICATION_MODE,
                },
                "safety": {
                    "raw_video_persistence": False,
                    "emergency_guarantee": False,
                    "human_review_required": True,
                },
            },
            status=200,
        )


class CapabilitiesView(APIView):
    """Make implementation boundaries visible to the dashboard and operators."""

    def get(self, request):  # noqa: ARG002
        return Response(
            {
                "service": "shade-ai-api",
                "activity_categories": ACTIVITY_CATEGORIES,
                "implemented": [
                    "api_health_diagnostics",
                    "mongodb_document_boundary",
                    "camera_configuration_boundary",
                    "emergency_event_boundary",
                    "temporal_fall_verification",
                    "monitoring_control_plane",
                    "synthetic_vision_source",
                ],
                "experimental": [
                    "websocket_monitoring_channel",
                    "opencv_camera_sources",
                    "rtmo_s_onnx_cpu_observation_adapter",
                    "ephemeral_iou_person_tracking",
                    "geometric_posture_heuristics_not_activity_model",
                ],
                "planned": [
                    "authenticated_operators",
                    "validated_model_and_training_data_rights",
                    "representative_fall_evaluation",
                    "multi-camera_monitoring",
                    "production_notification_provider",
                    "retention_scheduler",
                ],
                "configuration": {
                    "monitoring_mode": settings.MONITORING_MODE,
                    "notification_mode": settings.NOTIFICATION_MODE,
                },
            }
        )
