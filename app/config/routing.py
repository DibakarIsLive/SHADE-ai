"""WebSocket routes for live monitoring updates."""

from django.urls import re_path

from monitoring.consumers import MonitoringConsumer


websocket_urlpatterns = [
    re_path(r"^ws/monitoring/?$", MonitoringConsumer.as_asgi()),
]
