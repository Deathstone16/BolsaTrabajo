from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from .models import ResultadoCompatibilidad
from .services import status_payload


class MatchConsumer(AsyncJsonWebsocketConsumer):
    @database_sync_to_async
    def owned_match(self, user_id, request_id):
        return ResultadoCompatibilidad.objects.filter(
            request_id=request_id, postulante__usuario_id=user_id,
        ).first()

    async def connect(self):
        user = self.scope['user']
        request_id = self.scope['url_route']['kwargs']['request_id']
        if not user.is_authenticated:
            await self.close(code=4401)
            return
        match = await self.owned_match(user.pk, request_id)
        if match is None:
            await self.close(code=4404)
            return
        self.group_name = f'match-{request_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json(status_payload(match))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def match_update(self, event):
        await self.send_json(event['payload'])
