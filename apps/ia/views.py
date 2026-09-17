import json

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from usuarios.decorators import postulante_required

from .models import AnalisisCV
from .services import extraer_texto_cv


@login_required
@postulante_required
@require_POST
def solicitar_analisis(request):
    """Extrae el texto del CV y lo envía al servicio externo de análisis."""
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

    try:
        texto_cv = extraer_texto_cv(postulante.cv.path)
    except (OSError, ValueError):
        return JsonResponse({'success': False, 'mensaje': 'No se pudo leer el PDF del CV.'}, status=400)

    if not texto_cv:
        return JsonResponse({'success': False, 'mensaje': 'El PDF no contiene texto extraíble.'}, status=400)

    analisis = AnalisisCV.objects.create(postulante=postulante)
    payload = {
        'analysis_id': analisis.id,
        'candidate_id': postulante.id,
        'cv_text': texto_cv,
    }
    headers = {'Content-Type': 'application/json'}
    if settings.IA_API_TOKEN:
        headers['Authorization'] = f'Bearer {settings.IA_API_TOKEN}'

    try:
        respuesta = requests.post(settings.IA_API_URL, json=payload, headers=headers, timeout=30)
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
