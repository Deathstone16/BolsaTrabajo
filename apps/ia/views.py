"""Vistas reservadas para la futura interfaz del módulo de IA."""

import hashlib
import hmac
import json
import time
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from usuarios.decorators import postulante_required

from .models import AnalisisCV, TrabajoExtraccion
from .workflow import receive_extraction_event, request_cv_extraction, request_profile_normalization
from .forms import PerfilCVForm
from .models import PerfilCV


@login_required
@postulante_required
@require_POST
def solicitar_analisis(request):
    """Envía el PDF a FastAPI, que lo encola para extraerlo y analizarlo."""
    postulante = request.user.postulante

    if not postulante.cv:
        return JsonResponse({'success': False, 'mensaje': 'Primero debés cargar un CV.'}, status=400)
    if not postulante.cv.name.lower().endswith('.pdf'):
        return JsonResponse(
            {'success': False, 'mensaje': 'Por el momento el análisis admite CV en formato PDF.'},
            status=400,
        )
    if not settings.IA_API_URL or not settings.IA_API_TOKEN:
        return JsonResponse({'success': False, 'mensaje': 'El servicio de análisis no está configurado.'}, status=503)
    try:
        analisis, _, creado = request_cv_extraction(postulante)
    except OSError:
        return JsonResponse({'success': False, 'mensaje': 'No se pudo preparar el CV para analizar.'}, status=502)

    return JsonResponse({
        'success': True,
        'mensaje': 'CV preparado para analizar.' if creado else 'Ya hay un análisis de CV en proceso.',
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
    perfil = PerfilCV.objects.filter(postulante=analisis.postulante).first()
    return render(request, 'ia/resultado_analisis.html', {'analisis': analisis, 'perfil': perfil})


@login_required
@postulante_required
def editar_perfil_cv(request):
    profile = get_object_or_404(PerfilCV, postulante=request.user.postulante)
    if profile.estado == 'processing':
        messages.info(request, 'La edición anterior todavía se está normalizando.')
        return redirect('mi_perfil')
    if not profile.contenido:
        messages.error(request, 'Todavía no hay un perfil para editar.')
        return redirect('mi_perfil')
    if request.method == 'POST':
        form = PerfilCVForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['version'] != profile.version:
                form.add_error(None, 'Tu perfil cambió en otra sesión. Recargá la página antes de guardar.')
            else:
                content = form.apply_to(profile.contenido)
                request_profile_normalization(request.user.postulante, content, profile.version)
                messages.info(request, 'Guardamos tu edición. La estamos normalizando para usarla en compatibilidad.')
                return redirect('mi_perfil')
    else:
        form = PerfilCVForm(initial=PerfilCVForm.initial_from_profile(profile))
    return render(request, 'ia/editar_perfil_cv.html', {'form': form, 'perfil': profile})


@csrf_exempt
def llegue(request):
    """Callback que recibe y persiste el JSON generado por la API externa."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    timestamp = request.headers.get('X-IA-Event-Timestamp', '')
    signature = request.headers.get('X-IA-Callback-Signature', '')
    try:
        timestamp_value = int(timestamp)
    except ValueError:
        return JsonResponse({'detail': 'Timestamp de callback inválido.'}, status=401)
    if abs(time.time() - timestamp_value) > 300:
        return JsonResponse({'detail': 'Callback vencido.'}, status=401)
    secret = settings.IA_CALLBACK_HMAC_SECRET
    expected = hmac.new(
        secret.encode('utf-8'), timestamp.encode('ascii') + b'.' + request.body, hashlib.sha256
    ).hexdigest() if secret else ''
    if not secret or not signature or not hmac.compare_digest(signature, expected):
        return JsonResponse({'detail': 'No autorizado.'}, status=401)

    try:
        respuesta = json.loads(request.body)
        respuesta['event_id']
        respuesta['request_id']
        respuesta['source_hash']
    except (json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse({'detail': 'JSON inválido.'}, status=400)

    try:
        applied = receive_extraction_event(respuesta)
    except (TrabajoExtraccion.DoesNotExist, ValueError):
        return JsonResponse({'detail': 'Solicitud de extracción inexistente o inválida.'}, status=404)
    return JsonResponse({'success': True, 'duplicado': not applied})
