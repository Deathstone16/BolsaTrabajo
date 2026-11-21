"""Render the actual frontend templates with deterministic, synthetic fixtures."""
from types import SimpleNamespace as NS
from io import BytesIO
import re

from django import forms
from django.contrib.auth.models import AnonymousUser
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from ientrabajo.ui_review import SCREENS, COMPANY_PREVIEWS, company_preview
from .data import fixtures, SUMMARY
from .admin_views import ADMIN_TEMPLATES, admin_screen

TEMPLATES = {
    **ADMIN_TEMPLATES,
    'PUB-01': 'nueva_ui/home.html', 'PUB-02': 'nueva_ui/buscar_empleo.html',
    'PUB-03': 'nueva_ui/detalle_oferta.html', 'PUB-04': 'cursos/listado.html', 'PUB-05': 'cursos/detalle.html',
    'POS-01': 'usuarios/mi_perfil.html', 'POS-02': 'ia/perfil_profesional.html',
    'POS-03': 'ia/editar_perfil_cv.html', 'POS-04': 'ia/resultado_analisis.html',
    'POS-05': 'ia/editar_habilidades.html', 'POS-06': 'usuarios/datos_personales.html',
    'POS-07': 'usuarios/exito.html', 'POS-08': 'nueva_ui/favoritos.html', 'POS-09': 'matching/detalle.html',
    'ACC-01': 'usuarios/login.html', 'ACC-02': 'usuarios/registro.html', 'ACC-03': 'usuarios/exito.html',
    'ACC-04': 'usuarios/recuperar_contrasena.html', 'ACC-05': 'usuarios/recuperar_enviado.html',
    'ACC-06': 'usuarios/restablecer_contrasena.html', 'ACC-07': 'usuarios/contrasena_exitosa.html',
    'EMP-01': 'usuarios/registro.html', 'EMP-02': 'usuarios/exito.html',
}


class CourseFilters(forms.Form):
    q = forms.CharField(label='Buscar por título', required=False, widget=forms.TextInput(attrs={'placeholder': 'Ej. Excel, administración…'}))
    categoria = forms.ChoiceField(label='Categoría', required=False, choices=[('', 'Todas las categorías'), ('0', 'Tecnología')])
    modalidad = forms.ChoiceField(label='Modalidad', required=False, choices=[('', 'Todas'), ('Virtual', 'Virtual'), ('Presencial', 'Presencial')])
    duracion = forms.ChoiceField(label='Duración', required=False, choices=[('', 'Todas las duraciones'), ('4 semanas', '4 semanas'), ('8 semanas', '8 semanas'), ('12 semanas', '12 semanas')])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'input-ien'


def index(request):
    request.user = AnonymousUser()
    groups = []
    for group in ('Público', 'Acceso', 'Postulante', 'Empresa', 'Administración'):
        items = [{'screen': item, 'url': '', 'preview_url': reverse('design_demo_screen', args=[item.id]), 'reason': ''} for item in SCREENS if item.group == group and (item.id in TEMPLATES or item.id in COMPANY_PREVIEWS)]
        groups.append({'title': group, 'items': items})
    return render(request, 'nueva_ui/screen_index.html', {'screen_groups': groups, 'screen_count': sum(len(g['items']) for g in groups), 'review_role': 'Demo de diseño', 'design_demo': True})


def screen(request, screen_id):
    if screen_id in ADMIN_TEMPLATES:
        return admin_screen(request, screen_id)
    if screen_id in COMPANY_PREVIEWS:
        request.user = AnonymousUser()
        return company_preview(request, screen_id)
    if screen_id not in TEMPLATES:
        raise Http404
    from ia.forms import PerfilCVForm
    from ofertas.models import Oferta
    from usuarios.forms import CargaCVForm, DatosPersonalesForm, LoginForm, RegistroPostulanteForm, RegistroOferenteForm, PasswordResetRequestForm, SetPasswordForm
    data = fixtures()
    request.user = data['user']
    item = next(item for item in SCREENS if item.id == screen_id)
    courses = data['cursos']
    offers = data['ofertas']
    record_id = request.resolver_match.kwargs.get('pk', 0)
    selected_offer = next((offer for offer in offers if offer.pk == record_id), offers[0])
    selected_course = next((course for course in courses if course.pk == record_id), courses[0])
    query = request.GET.get('q', '').strip().casefold()
    selected_offers = [offer for offer in offers if query in ' '.join([offer.titulo, offer.descripcion, offer.empresa.oferente.nombre_empresa, offer.habilidades_duras, offer.habilidades_blandas]).casefold()]
    for param, field in [('ubicacion', 'ubicacion'), ('modalidad', 'modalidad'), ('experiencia', 'experiencia_requerida')]:
        if value := request.GET.get(param):
            selected_offers = [offer for offer in selected_offers if value.casefold() in getattr(offer, field).casefold()]
    selected_courses = [course for course in courses if query in course.nombre.casefold()]
    for param, field in [('modalidad', 'tipo'), ('duracion', 'duracion'), ('categoria', 'categoria_id')]:
        if value := request.GET.get(param):
            selected_courses = [course for course in selected_courses if str(getattr(course, field)) == value]
    context = {
        **data, 'user': data['user'], 'oferta': selected_offer, 'curso': selected_course,
        'ofertas': selected_offers if screen_id == 'PUB-02' else offers[:2], 'total': 2,
        'q': request.GET.get('q', ''), 'ubicacion': request.GET.get('ubicacion', ''), 'vista_activa': 'inicio' if screen_id == 'PUB-01' else 'cursos' if screen_id in ('PUB-04', 'PUB-05') else 'buscar',
        'ofertas_destacadas': offers, 'total_ofertas': len(offers), 'total_empresas': 1, 'total_cursos': len(courses),
        'cursos': selected_courses if screen_id == 'PUB-04' else courses,
        'filtros': CourseFilters(request.GET), 'filtros_cursos': CourseFilters(auto_id='home-curso-%s'),
        'total_resultados': len(selected_courses), 'pagina': Paginator(selected_courses, 9).get_page(1),
        'hay_filtros': bool(request.GET), 'modalidad_choices': Oferta.MODALIDAD_CHOICES, 'experiencia_choices': Oferta.EXPERIENCIA_CHOICES,
        'version_cv_actual': data['version'], 'historial_cv': [data['version']], 'ultimo_analisis': data['analisis'], 'perfil_cv': data['perfil'],
        'resumen_profesional': SUMMARY, 'es_version_actual': True, 'cv_formatos': ['pdf', 'docx'],
        'ui_review_screen': item, 'ui_review_preview': True, 'design_demo': True,
        'form': CargaCVForm(), 'niveles_habilidad': ['Básico', 'Intermedio', 'Avanzado'],
        'mostrar_menu_postulante': screen_id == 'POS-07',
        'titulo': 'Datos guardados', 'mensaje': 'Tus datos personales se actualizaron correctamente.',
        'link_url': reverse('design_demo_screen', args=['POS-06']), 'link_texto': 'Volver a mis datos',
        'perfil_oferta': NS(estado='ready', schema_version='job-offer.v2'),
    }
    if screen_id == 'POS-01':
        state = request.GET.get('estado', 'completado')
        if state == 'sin-cv':
            context.update(version_cv_actual=None, perfil_cv=None, ultimo_analisis=None, historial_cv=[])
        elif state in ('pendiente', 'error'):
            data['analisis'].estado = state
            context['perfil_cv'] = None
    if screen_id == 'POS-03':
        context['form'] = PerfilCVForm(initial=PerfilCVForm.initial_from_profile(data['perfil']))
    elif screen_id == 'POS-06':
        context['form'] = DatosPersonalesForm(instance=data['postulante'], initial={'first_name': 'Lucía', 'last_name': 'Gómez', 'email': data['user'].email})
    elif screen_id == 'PUB-03':
        context.update(habilidades_duras=['Python', 'Excel', 'SQL'], habilidades_blandas=['Comunicación', 'Trabajo en equipo'])
    elif screen_id == 'POS-09':
        context.update(match_context(data))
    elif screen_id.startswith('ACC-') or screen_id in ('EMP-01', 'EMP-02'):
        request.user = AnonymousUser()
        context['user'] = request.user
        context['tipo'] = item.query or 'postulante'
        context['form'] = {
            'ACC-01': LoginForm, 'ACC-02': RegistroPostulanteForm, 'EMP-01': RegistroOferenteForm,
            'ACC-04': PasswordResetRequestForm,
        }.get(screen_id, LoginForm)()
        if screen_id == 'ACC-06':
            context['form'] = SetPasswordForm(data['user'])
        if screen_id in ('ACC-03', 'EMP-02'):
            context.update(titulo='Empresa registrada' if screen_id == 'EMP-02' else 'Tu cuenta está lista', mensaje='El equipo del IEN está revisando tu empresa.' if screen_id == 'EMP-02' else 'Ya podés completar tu perfil y explorar oportunidades.', pendiente_validacion=screen_id == 'EMP-02', link_url=reverse('design_demo_screen', args=['EMP-03' if screen_id == 'EMP-02' else 'POS-01']), link_texto='Continuar')
    response = render(request, TEMPLATES[screen_id], context)
    # Use a real synthetic PDF instead of a private storage download route.
    html = response.content.decode(response.charset).replace(reverse('descargar_cv', args=[0]), reverse('design_demo_cv'))
    # Integration scripts would poll endpoints and overwrite the fixed results.
    html = re.sub(r'<script\b[^>]*src="[^"]*(?:cv_upload|matching|cv_notifications)[^"]*"[^>]*></script>', '', html)
    response.content = html
    return response


def match_context(data):
    assessments = [
        {'name': 'Python', 'status': 'met', 'status_label': 'Coincide', 'explanation': 'El CV de ejemplo incluye automatización de reportes con Python.', 'points_awarded': 35, 'points_possible': 35},
        {'name': 'Excel avanzado', 'status': 'met', 'status_label': 'Coincide', 'explanation': 'Hay experiencia con tablas dinámicas y tableros.', 'points_awarded': 30, 'points_possible': 30},
        {'name': 'SQL', 'status': 'partial', 'status_label': 'Coincide parcialmente', 'explanation': 'El perfil menciona consultas básicas. Se puede reforzar el análisis con consultas más complejas.', 'points_awarded': 7, 'points_possible': 15},
        {'name': 'Comunicación', 'status': 'met', 'status_label': 'Coincide', 'explanation': 'Presentación de resultados a equipos comerciales.', 'points_awarded': 10, 'points_possible': 20},
    ]
    return {
        'result': {'summary': 'Tu perfil tiene una buena base para esta oportunidad. Python y Excel coinciden con lo solicitado; SQL es un área para seguir fortaleciendo.'},
        'mandatory_label': 'Se cumplen los requisitos obligatorios',
        'unused_dimensions': [],
        'groups': [{'title': 'Requisitos obligatorios', 'items': assessments[:2]}, {'title': 'Requisitos deseables', 'items': assessments[2:]}],
        'breakdown': [{'label': label, 'percentage': pct, 'weight': weight, 'applicable': True} for label, pct, weight in [('Competencias técnicas', 80, 60), ('Habilidades blandas', 80, 15), ('Experiencia', 80, 15), ('Educación', 100, 10)]],
        'course_recommendations': {'has_gaps': True, 'courses': [{'course': data['cursos'][3], 'match_type': 'related', 'reason': 'Opción de ejemplo para profundizar herramientas de análisis.', 'gaps': [assessments[2]]}]},
    }


def health(request):
    return HttpResponse('Demo de diseño disponible', content_type='text/plain')


def cv(request):
    # Generate a tiny deterministic PDF from fictional text, without files or uploads.
    lines = ['Lucia Gomez - CV de ejemplo', 'DATOS FICTICIOS - DEMO DE DISENO', 'Analista de datos | Resistencia, Chaco', 'Contacto: lucia.demo@example.com', '', 'Experiencia: Analista de reportes - 2024 a 2026', 'Python, Excel y SQL. Automatizacion de reportes.', '', 'Estudios: Tecnicatura en Analisis de Sistemas.', 'Idiomas: Espanol nativo e Ingles conversacional.']
    stream = 'BT /F1 16 Tf 50 780 Td ' + ' '.join(('0 -26 Td ' if i else '') + '(' + line + ') Tj' for i, line in enumerate(lines)) + ' ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>', b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>', b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', f'<< /Length {len(stream)} >>\nstream\n{stream}\nendstream'.encode('ascii')]
    output = BytesIO(b'%PDF-1.4\n')
    output.seek(0, 2)
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(output.tell())
        output.write(f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n')
    start = output.tell()
    output.write(b'xref\n0 6\n0000000000 65535 f \n' + b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:]))
    output.write(f'trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF'.encode())
    response = HttpResponse(output.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="CV_Lucia_Gomez_DEMO.pdf"'
    return response
