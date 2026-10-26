from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from usuarios.decorators import postulante_required
from ofertas.models import Oferta

from .models import ResultadoCompatibilidad
from .services import get_or_create_match, status_payload, cancel_match
from .course_recommendations import recommend_courses_for_match


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


@login_required
@postulante_required
@require_POST
def cancelar_compatibilidad(request, request_id):
    get_object_or_404(ResultadoCompatibilidad, request_id=request_id, postulante=request.user.postulante)
    match = cancel_match(request_id, request.user.postulante)
    return JsonResponse({'success': True, **status_payload(match)})


@login_required
@postulante_required
@require_GET
def detalle_compatibilidad(request, request_id):
    match = get_object_or_404(
        ResultadoCompatibilidad.objects.select_related('oferta__categoria'),
        request_id=request_id, postulante=request.user.postulante,
    )
    result = (match.resultado or {}) if match.estado == 'completed' else {}
    dimensions = {
        'technical_skills': 'Competencias técnicas', 'soft_skills': 'Habilidades blandas',
        'experience': 'Experiencia', 'education': 'Educación', 'languages': 'Idiomas',
        'logistics': 'Logística y modalidad', 'desirables': 'Requisitos deseables',
    }
    statuses = {'met': 'Coincide', 'partial': 'Coincide parcialmente',
                'not_met': 'No alcanza el nivel requerido', 'unknown': 'Sin información suficiente'}
    groups = []
    for mandatory, title in ((True, 'Requisitos obligatorios'), (False, 'Requisitos deseables')):
        items = [{**item, 'status_label': statuses.get(item['status'], 'Sin información suficiente')}
                 for item in result.get('assessments', []) if item['mandatory'] == mandatory]
        groups.append({'title': title, 'items': items})
    breakdown = [{**value, 'label': dimensions.get(key, key),
                  'percentage': round(value['score'] * 100),
                  'weight': value['configured_weight_bp'] / 100}
                 for key, value in result.get('breakdown', {}).items()]
    mandatory_labels = {'all_met': 'Se cumplen los requisitos obligatorios',
                        'not_met': 'Hay requisitos obligatorios que no se cumplen',
                        'unknown': 'Falta información para confirmar los requisitos obligatorios'}
    return render(request, 'matching/detalle.html', {
        'vista_activa': 'buscar', 'match': match, 'result': result,
        'groups': groups, 'breakdown': breakdown,
        'course_recommendations': recommend_courses_for_match(match),
        'mandatory_label': mandatory_labels.get(result.get('mandatory_status'), 'Sin requisitos obligatorios'),
    })
