"""HTTP-only entrypoint: no live CV or matching websocket consumers."""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ientrabajo.settings.design_demo')
application = get_asgi_application()
