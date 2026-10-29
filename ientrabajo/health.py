"""Comprobación acotada de los servicios necesarios para la web."""

from django.conf import settings
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from redis import Redis, RedisError


@require_safe
@never_cache
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        with Redis.from_url(settings.CHANNEL_REDIS_URL, socket_connect_timeout=2,
                            socket_timeout=2) as client:
            client.ping()
    except (DatabaseError, RedisError):
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})
