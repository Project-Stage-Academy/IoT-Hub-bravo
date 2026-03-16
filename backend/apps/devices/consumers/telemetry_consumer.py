import json
import logging
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.devices.models import Device
from apps.users.models import UserRole

logger = logging.getLogger(__name__)


@sync_to_async
def _device_belongs_to_user(device_serial_id: str, user) -> bool:
    return Device.objects.filter(
        serial_id=device_serial_id,
        user=user,
        is_active=True,
    ).exists()


class TelemetryConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for telemetry stream. Requires JWT with claim 'role' (admin/client).
    Close codes 4401/4403/4404 are application-specific (RFC 6455 allows 4xxx for app use).
    """

    ALLOWED_ROLES = {"admin", "client"}
    BASE_GROUP = "telemetry.global"

    async def connect(self):
        user = self.scope.get("user")
        role = self.scope.get("role")

        if not (user and user.is_authenticated):
            await self.close(code=4401)
            return

        if role not in self.ALLOWED_ROLES:
            await self.close(code=4403)
            return

        if self.channel_layer is None:
            await self.close(code=4404)
            return

        params = parse_qs(self.scope.get("query_string", b"").decode())
        device = (params.get("device", [None])[0] or "").strip()
        metric = (params.get("metric", [None])[0] or "").strip()

        # Device-level authorization: non-admin users can subscribe only to their own devices
        if device and role != UserRole.ADMIN:
            try:
                allowed = await _device_belongs_to_user(device, user)
            except Exception as e:
                logger.error("Error checking device ownership for '%s': %s", device, e)
                await self.close(code=4500)
                return

            if not allowed:
                logger.warning(
                    "User %s (role=%s) attempted to subscribe to unauthorized device '%s'",
                    getattr(user, "id", None),
                    role,
                    device,
                )
                await self.close(code=4403)
                return

        self.groups_to_join = [self.BASE_GROUP]
        if device:
            self.groups_to_join.append(f"telemetry.device.{device}")
        if metric:
            self.groups_to_join.append(f"telemetry.metric.{metric}")

        try:
            for group_name in self.groups_to_join:
                await self.channel_layer.group_add(group_name, self.channel_name)
        except Exception as e:
            logger.error("Error connecting to telemetry stream: %s", e)
            await self.close(code=4500)
            return

        await self.accept()

    async def disconnect(self, close_code):
        if self.channel_layer is not None:
            for group_name in getattr(self, "groups_to_join", []):
                await self.channel_layer.group_discard(group_name, self.channel_name)

    async def telemetry_update(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
