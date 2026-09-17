import json

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from usuarios.decorators import postulante_required

from .models import AnalisisCV


@login_required
@postulante_required
@require_POST
def solicitar_analisis(request):
    """Envía el PDF del CV a FastAPI para que lo extraiga y analice."""
    postulante = request.user.postulante

    if not postulante.cv:
        return JsonResponse({'success': False, 'mensaje': 'Primero debés cargar un CV.'}, status=400)
    if not postulante.cv.name.lower().endswith('.pdf'):
        return JsonResponse(
            {'success': False, 'mensaje': 'Por el momento el análisis admite CV en formato PDF.'},
            status=400,
        )
    if not settings.IA_API_URL:
        return JsonResponse({'success': False, 'mensaje': 'El servicio de análisis no está configurado.'}, status=503)

    analisis = AnalisisCV.objects.create(postulante=postulante)
    data = {
        'analysis_id': analisis.id,
        'candidate_id': postulante.id,
    }
    headers = {}
    if settings.IA_API_TOKEN:
        headers['Authorization'] = f'Bearer {settings.IA_API_TOKEN}'

    try:
        with postulante.cv.open('rb') as cv_file:
            files = {
                'cv': (
                    postulante.cv.name.rsplit('/', 1)[-1],
                    cv_file,
                    'application/pdf',
                )
            }
            respuesta = requests.post(
                settings.IA_API_URL,
                data=data,
                files=files,
                headers=headers,
                timeout=30,
            )
            respuesta.raise_for_status()
    except requests.RequestException as exc:
        analisis.estado = AnalisisCV.Estado.ERROR
        analisis.error = str(exc)
        analisis.save(update_fields=['estado', 'error'])
        return JsonResponse({'success': False, 'mensaje': 'No se pudo enviar el CV al servicio de análisis.'}, status=502)

    return JsonResponse({
        'success': True,
        'mensaje': 'CV enviado para analizar.',
        'analisis_id': analisis.id,
    }, status=202)


@login_required
@postulante_required
def estado_analisis(request, analisis_id):
    """Devuelve el estado para que el botón pueda actualizarse sin recargar."""
    analisis = get_object_or_404(
        AnalisisCV,
        pk=analisis_id,
        postulante=request.user.postulante,
    )
    data = {
        'estado': analisis.estado,
        'mensaje': '',
        'resultado_url': None,
    }
    if analisis.estado == AnalisisCV.Estado.COMPLETADO:
        data['mensaje'] = 'El análisis del CV está listo.'
        data['resultado_url'] = reverse('ia:ver_resultado', args=[analisis.id])
    elif analisis.estado == AnalisisCV.Estado.ERROR:
        data['mensaje'] = analisis.error or 'No se pudo analizar el CV.'
    else:
        data['mensaje'] = 'Analizando CV…'
    return JsonResponse(data)


@login_required
@postulante_required
def ver_resultado(request, analisis_id):
    """Muestra el resultado de un análisis que pertenece al postulante actual."""
    analisis = get_object_or_404(
        AnalisisCV,
        pk=analisis_id,
        postulante=request.user.postulante,
    )
    return render(request, 'ia/resultado_analisis.html', {'analisis': analisis})


@csrf_exempt
def llegue(request):
    """Callback que recibe y persiste el JSON generado por la API externa."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    if not settings.IA_CALLBACK_TOKEN or request.headers.get('X-IA-Callback-Token') != settings.IA_CALLBACK_TOKEN:
        return JsonResponse({'detail': 'No autorizado.'}, status=401)

    try:
        respuesta = json.loads(request.body)
        analisis_id = respuesta['analysis_id']
    except (json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse({'detail': 'JSON inválido: falta analysis_id.'}, status=400)

    try:
        analisis = AnalisisCV.objects.get(pk=analisis_id)
    except AnalisisCV.DoesNotExist:
        return JsonResponse({'detail': 'Solicitud de análisis inexistente.'}, status=404)

    analisis.respuesta = respuesta
    if respuesta.get('status') == 'completed':
        analisis.estado = AnalisisCV.Estado.COMPLETADO
        analisis.error = ''
    else:
        analisis.estado = AnalisisCV.Estado.ERROR
        analisis.error = respuesta.get('error') or 'El servicio de análisis informó un error.'
    analisis.respondido_en = timezone.now()
    analisis.save(update_fields=['respuesta', 'estado', 'error', 'respondido_en'])
    return JsonResponse({'success': True, 'analisis_id': analisis.id})
