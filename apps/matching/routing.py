from django.urls import path

from .consumers import MatchConsumer


websocket_urlpatterns = [
    path('ws/matches/<uuid:request_id>/', MatchConsumer.as_asgi()),
]
