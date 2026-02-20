import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer


class TelemetryConsumer(AsyncWebsocketConsumer):
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

        params = parse_qs(self.scope.get("query_string", b"").decode())
        device = (params.get("device", [None])[0] or "").strip()
        metric = (params.get("metric", [None])[0] or "").strip()

        self.groups_to_join = [self.BASE_GROUP]
        if device:
            self.groups_to_join.append(f"telemetry.device.{device}")
        if metric:
            self.groups_to_join.append(f"telemetry.metric.{metric}")

        for group_name in self.groups_to_join:
            await self.channel_layer.group_add(group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        for group_name in getattr(self, "groups_to_join", []):
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def telemetry_update(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
