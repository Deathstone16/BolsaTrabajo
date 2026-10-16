from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from usuarios.decorators import postulante_required
from ofertas.models import Oferta

from .models import ResultadoCompatibilidad
from .services import get_or_create_match, status_payload


@login_required
@postulante_required
@require_POST
def calcular_compatibilidad(request, oferta_id):
    oferta = get_object_or_404(Oferta, pk=oferta_id, estado='activa')
    try:
        match, created = get_or_create_match(request.user.postulante, oferta)
    except ValueError as exc:
        return JsonResponse({'success': False, 'mensaje': str(exc)}, status=409)
    return JsonResponse({'success': True, 'created': created, **status_payload(match)}, status=202 if match.estado != 'completed' else 200)


@login_required
@postulante_required
@require_GET
def estado_compatibilidad(request, request_id):
    match = get_object_or_404(ResultadoCompatibilidad, request_id=request_id, postulante=request.user.postulante)
    return JsonResponse(status_payload(match))
