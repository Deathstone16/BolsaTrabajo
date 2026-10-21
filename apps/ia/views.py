"""Vistas reservadas para la futura interfaz del módulo de IA."""

import hashlib
import hmac
import json
import logging
import time
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

from usuarios.decorators import postulante_required

from .models import AnalisisCV, TrabajoExtraccion
from .workflow import receive_extraction_event, request_cv_extraction, request_profile_normalization
from .forms import PerfilCVForm
from .models import PerfilCV
from .profile_skills import split_profile_skills


NIVELES_HABILIDAD = ('Teórico', 'Principiante', 'Intermedio', 'Avanzado')
logger = logging.getLogger(__name__)
ANALYSIS_IN_PROGRESS_MESSAGE = 'Puede tardar varios minutos según la disponibilidad del servicio.'


@login_required
@postulante_required
@require_POST
def solicitar_analisis(request):

    """Envía el PDF a FastAPI, que lo encola para extraerlo y analizarlo."""
    postulante = request.user.postulante

    if not postulante.cv_version_actual_id:
        return JsonResponse({'success': False, 'mensaje': 'Primero debés cargar un CV.'}, status=400)

    if not settings.IA_API_URL:
        return JsonResponse({'success': False, 'mensaje': 'El servicio de análisis no está configurado.'}, status=503)
    try:
        analisis, _, creado = request_cv_extraction(postulante)
    except ValueError as exc:
        return JsonResponse({'success': False, 'mensaje': str(exc)}, status=409)
    except OSError:
        return JsonResponse({'success': False, 'mensaje': 'No se pudo preparar el CV para analizar.'}, status=502)

    return JsonResponse({
        'success': True,
        'mensaje': 'CV preparado para analizar.' if creado else 'Ya hay un análisis de CV en proceso.',
        'analisis_id': analisis.id,
        'version_cv_id': analisis.version_cv_id,
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
        'version_cv_id': analisis.version_cv_id,
        'es_version_actual': analisis.version_cv_id == request.user.postulante.cv_version_actual_id,
        'mensaje': '',
        'resultado_url': None,
    }
    if not data['es_version_actual']:
        data['mensaje'] = 'Este análisis corresponde a una versión anterior del CV.'
    elif analisis.estado == AnalisisCV.Estado.COMPLETADO:
        data['mensaje'] = 'El análisis del CV está listo.'
        data['resultado_url'] = reverse('ia:ver_resultado', args=[analisis.id])
    elif analisis.estado == AnalisisCV.Estado.ERROR:
        data['mensaje'] = analisis.error or 'No se pudo analizar el CV.'
    else:
        data['mensaje'] = ANALYSIS_IN_PROGRESS_MESSAGE
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
    perfil = None
    contenido_historico = analisis.perfil_snapshot
    if contenido_historico:
        from types import SimpleNamespace
        perfil = SimpleNamespace(contenido=contenido_historico)
    habilidades_duras, habilidades_blandas = split_profile_skills(contenido_historico or {})
    return render(request, 'ia/resultado_analisis.html', {
        'analisis': analisis,
        'perfil': perfil,
        'es_version_actual': analisis.version_cv_id == analisis.postulante.cv_version_actual_id,
        'habilidades_duras': habilidades_duras,
        'habilidades_blandas': habilidades_blandas,
    })


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


@login_required
@postulante_required
@require_http_methods(['GET', 'POST'])
def editar_habilidades(request, analisis_id):
    """Permite revisar y guardar todas las habilidades en una sola página."""
    analisis = get_object_or_404(
        AnalisisCV,
        pk=analisis_id,
        postulante=request.user.postulante,
        estado=AnalisisCV.Estado.COMPLETADO,
    )
    respuesta = analisis.respuesta
    resultado = respuesta.get('result') if isinstance(respuesta, dict) else None
    habilidades = resultado.get('habilidades_analizadas') if isinstance(resultado, dict) else None
    if not isinstance(habilidades, list) or any(not isinstance(h, dict) for h in habilidades):
        return HttpResponseBadRequest('El análisis no contiene una lista de habilidades válida.')

    if request.method == 'POST':
        cambios = []
        for indice, _ in enumerate(habilidades):
            opinion = request.POST.get(f'opinion_{indice}', '')
            nivel = request.POST.get(f'nivel_{indice}')
            if opinion not in ('', 'si', 'no') or nivel not in NIVELES_HABILIDAD:
                return HttpResponseBadRequest('Seleccioná una opinión y un nivel válidos.')
            cambios.append((opinion, nivel))

        for habilidad, (opinion, nivel) in zip(habilidades, cambios):
            if opinion:
                habilidad['acuerdo_usuario'] = opinion
            else:
                habilidad.pop('acuerdo_usuario', None)
            habilidad['nivel_usuario'] = nivel
        analisis.save(update_fields=['respuesta'])
        messages.success(request, 'Tus habilidades se guardaron correctamente.')
        return redirect('ia:ver_resultado', analisis_id=analisis.id)

    return render(request, 'ia/editar_habilidades.html', {
        'analisis': analisis,
        'habilidades': habilidades,
        'niveles_habilidad': NIVELES_HABILIDAD,
    })


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
    if applied:
        job = TrabajoExtraccion.objects.select_related('analisis_cv__postulante').filter(
            clave_idempotencia=respuesta['request_id'],
            source_hash=respuesta['source_hash'],
            tipo=TrabajoExtraccion.Tipo.CV,
        ).first()
        if job and job.analisis_cv:
            analysis = job.analisis_cv
            notification = {
                'analysis_id': analysis.pk,
                'version_cv_id': analysis.version_cv_id,
                'es_version_actual': analysis.version_cv_id == analysis.postulante.cv_version_actual_id,
                'status': analysis.estado,
                'mensaje': 'El análisis del CV está listo.' if analysis.estado == AnalisisCV.Estado.COMPLETADO
                           else (analysis.error or 'No se pudo analizar el CV.'),
                'resultado_url': reverse('ia:ver_resultado', args=[analysis.pk])
                                 if analysis.estado == AnalisisCV.Estado.COMPLETADO and analysis.version_cv_id == analysis.postulante.cv_version_actual_id else None,
            }
            try:
                async_to_sync(get_channel_layer().group_send)(
                    f'user_{analysis.postulante.usuario_id}',
                    {'type': 'cv.analysis.complete', 'payload': notification},
                )
            except Exception:
                logger.exception('No se pudo emitir la notificación del análisis de CV %s', analysis.pk)
    return JsonResponse({'success': True, 'duplicado': not applied})
