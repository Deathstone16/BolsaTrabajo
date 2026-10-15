from django.urls import path

from .consumers import CVAnalysisConsumer

websocket_urlpatterns = [
    path('ws/cv-analysis/', CVAnalysisConsumer.as_asgi()),
]
