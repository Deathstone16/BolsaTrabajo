"""Superadmin proxy: browser clients never receive the service credential."""
from urllib.parse import urlsplit, urlunsplit
import requests
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.template.response import TemplateResponse


def monitor_page(site, request):
    return TemplateResponse(request, 'admin/ia/token_monitor.html', {
        **site.each_context(request), 'title': 'Consumo de tokens de IA',
    })


def monitor_data(request):
    cached = cache.get('ia-token-monitor:v1')
    if cached is not None:
        return JsonResponse(cached)
    if not settings.IA_API_URL:
        return JsonResponse({'message': 'El servicio de IA no está configurado.'}, status=503)
    source = urlsplit(settings.IA_API_URL.rstrip('/'))
    url = urlunsplit((source.scheme, source.netloc, source.path.rsplit('/', 1)[0] + '/llm-usage', '', ''))
    try:
        response = requests.get(url, headers={'Authorization': f'Bearer {settings.IA_API_TOKEN}'},
                                timeout=(2, 5), allow_redirects=False)
        response.raise_for_status()
        body = response.json()
        if response.status_code != 200 or not isinstance(body, dict):
            raise ValueError
        # Fixed top-level contract: never proxy an upstream error body or result.
        result = {key: body.get(key) for key in ('generated_at', 'started_at', 'totals', 'models', 'hours', 'routes', 'vercel_enabled')}
        if not isinstance(result['totals'], dict) or not all(isinstance(result[name], list) for name in ('models','hours','routes')):
            raise ValueError
    except (requests.RequestException, ValueError, TypeError):
        return JsonResponse({'message': 'No se pudo consultar el consumo de IA. Se volverá a intentar.'}, status=503)
    cache.set('ia-token-monitor:v1', result, timeout=10)
    response = JsonResponse(result)
    response['Cache-Control'] = 'no-store'
    return response
