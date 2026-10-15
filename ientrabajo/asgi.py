"""
ASGI config for ientrabajo project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ientrabajo.settings.base')

django_asgi_app = get_asgi_application()
from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

if settings.DEBUG:
    django_asgi_app = ASGIStaticFilesHandler(django_asgi_app)

from matching.routing import websocket_urlpatterns
from django.urls import path
from ia.consumers import CVNotificationConsumer

websocket_urlpatterns = [*websocket_urlpatterns, path('ws/cv/', CVNotificationConsumer.as_asgi())]

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
})
