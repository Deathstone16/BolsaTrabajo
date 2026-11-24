"""Read-only monitoring: never submits inference or changes job state."""
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.cache import cache


LABELS = {
    'accepted': 'Aceptado; pendiente de ejecución',
    'queued': 'En cola',
    'processing': 'Procesando',
    'rate_limited': 'Esperando capacidad o cuota',
    'completed': 'Análisis terminado',
    'failed': 'Análisis fallido',
}


def remote_status(job):
    if not job.remote_job_id:
        return {'status': 'pending', 'message': 'Pendiente de envío'}
    key = f'cv-monitor:{job.pk}:{job.remote_job_id}'
    cached = cache.get(key)
    if cached is not None:
        return cached
    if not settings.IA_API_URL:
        return {'status': 'unavailable', 'message': 'Servicio IA sin configurar'}
    url = settings.IA_API_URL.rstrip('/') + '/' + quote(job.remote_job_id, safe='')
    try:
        response = requests.get(url, headers={'Authorization': f'Bearer {settings.IA_API_TOKEN}'},
                                timeout=(2, 3), allow_redirects=False)
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError('Unexpected status')
        body = response.json()
        state = body.get('status')
        result = {'status': state if state in LABELS else 'unknown',
                  'message': LABELS.get(state, 'Estado no reconocido')}
        if state == 'completed' and not body.get('delivered'):
            result['message'] = 'Análisis terminado; entrega pendiente'
        for field in ('completed_packets', 'total_packets', 'retry_after_seconds'):
            value = body.get(field)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                result[field] = value
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        result = {'status': 'unavailable', 'message': 'No se pudo consultar IA; el trabajo conserva su estado'}
    cache.set(key, result, timeout=10)
    return result
