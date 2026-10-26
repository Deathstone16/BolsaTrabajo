"""Render health probe alongside the application's existing routes."""

from pathlib import Path

from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.conf import settings
from django.urls import include, path
from django.views.decorators.http import require_safe
from django.views.static import serve


@require_safe
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except DatabaseError:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})


def analysis_unavailable(_request):
    return JsonResponse({'success': False, 'mensaje': 'El análisis de CV no está disponible en esta demo.'}, status=503)


urlpatterns = [
    path('health', health),
    path('ia/solicitar-analisis/', analysis_unavailable),
    path('media/cursos/<path:path>', serve, {'document_root': Path(settings.MEDIA_ROOT) / 'cursos'}),
    path('media/empresas/<path:path>', serve, {'document_root': Path(settings.MEDIA_ROOT) / 'empresas'}),
    path('', include('ientrabajo.urls')),
]
