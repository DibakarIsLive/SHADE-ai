"""Read-only WebSocket boundary for future live monitoring events."""

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from monitoring.runtime import monitoring_controller


class MonitoringConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send_json(
            {
                "type": "monitoring.snapshot",
                "payload": monitoring_controller.snapshot(),
            }
        )

    async def receive_json(self, content, **kwargs):  # noqa: ARG002
        # The first slice is intentionally read-only. Control mutations stay on
        # authenticated HTTP/worker boundaries instead of an unauthenticated socket.
        await self.send_json(
            {
                "type": "monitoring.notice",
                "payload": {
                    "message": "The monitoring socket is read-only in this slice.",
                    "received_type": content.get("type") if isinstance(content, dict) else None,
                },
            }
        )
