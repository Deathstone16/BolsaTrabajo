"""Error pages that work without sessions, context processors or a database."""
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_safe

ERRORS = {
    'offline': ('Sin conexión', 'No pudimos conectarnos', 'Revisá tu conexión a internet y volvé a intentarlo. Si estabas enviando datos, comprobá su estado antes de reenviarlos.'),
    400: ('Solicitud inválida', 'No pudimos abrir esta solicitud', 'Revisá la dirección o volvé al inicio para continuar.'),
    403: ('Acceso restringido', 'No tenés acceso a esta página', 'Ingresá con una cuenta autorizada o volvé al inicio.'),
    404: ('Página no encontrada', 'Esta página no llegó a destino', 'El enlace puede haber cambiado o la página ya no está disponible.'),
    500: ('Error del servidor', 'Algo no salió como esperábamos', 'No pudimos completar la solicitud. Volvé al inicio e intentá nuevamente en unos minutos.'),
    503: ('Servicio no disponible', 'Estamos haciendo una pausa', 'La plataforma no está disponible en este momento. Intentá nuevamente en unos minutos.'),
    504: ('Tiempo de espera agotado', 'La respuesta está tardando demasiado', 'No pudimos confirmar el resultado. Revisá el estado de tu operación antes de volver a enviarla.'),
}


def error_context(status, preview_id=None, retry_url=None):
    label, title, description = ERRORS[status]
    return dict(label=label, title=title, description=description, preview_id=preview_id, retry_url=retry_url)


def render_error(request, status, *, preview_id=None):
    # Do not expose exception text, URL query parameters, form values or tokens.
    context = error_context(status, preview_id, request.path if status in (500, 503, 504, 'offline') and request.method in ('GET', 'HEAD') and not request.path.startswith('/estado/') else None)
    if not preview_id and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = JsonResponse({'success': False, 'mensaje': context['description']}, status=status)
    else:
        response = HttpResponse(render_to_string('errors/page.html', context), status=200 if preview_id else status)
    response['Cache-Control'] = 'no-store'
    if status == 503 and not preview_id:
        response['Retry-After'] = '60'
    response.ien_error_page = True
    return response


def bad_request(request, exception=None): return render_error(request, 400)
def permission_denied(request, exception=None): return render_error(request, 403)
def not_found(request, exception=None): return render_error(request, 404)
def server_error(request): return render_error(request, 500)
def csrf_failure(request, reason=''): return render_error(request, 403)


@require_safe
def unavailable(request): return render_error(request, 503)


@require_safe
def timeout(request): return render_error(request, 504)


class ServerErrorPageMiddleware:
    """Style explicit HTML server errors while preserving JSON API contracts."""
    def __init__(self, get_response): self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code in (500, 503, 504) and not getattr(response, 'ien_error_page', False) and response.get('Content-Type', '').startswith('text/html') and not response.streaming:
            replacement = render_error(request, response.status_code)
            response.content = replacement.content
            response['Content-Type'] = replacement['Content-Type']
            response['Cache-Control'] = 'no-store'
            if response.has_header('Content-Length'): del response['Content-Length']
        return response
