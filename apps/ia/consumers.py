from urllib.parse import parse_qs

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core import signing


TOKEN_SALT = 'ia.cv-analysis.websocket'
TOKEN_MAX_AGE = 60 * 60


class CVAnalysisConsumer(AsyncJsonWebsocketConsumer):
    """Sólo la sesión autenticada puede escuchar los eventos de su usuario."""

    async def connect(self):
        user = self.scope['user']
        query = parse_qs(self.scope.get('query_string', b'').decode('utf-8'))
        token = query.get('token', [''])[0]
        try:
            signed_user_id = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
        except (signing.BadSignature, signing.SignatureExpired):
            await self.close(code=4401)
            return
        if not user.is_authenticated or signed_user_id != user.pk:
            await self.close(code=4401)
            return

        self.group_name = f'user_{user.pk}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def cv_analysis_complete(self, event):
        await self.send_json({'type': 'cv.analyzed', 'payload': event['payload']})
