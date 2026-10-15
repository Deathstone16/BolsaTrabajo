from channels.generic.websocket import AsyncJsonWebsocketConsumer


class CVNotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close(code=4401)
            return
        self.group_name = f'user_{user.pk}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def cv_analysis_complete(self, event):
        await self.send_json(event['payload'])
