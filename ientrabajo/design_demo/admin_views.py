"""Institute admin screens, rendered from synthetic data without DB access."""
from copy import copy

from django.core.paginator import Paginator
from django.shortcuts import render
from django.urls import reverse

from categorias.models import Habilidad
from cursos.forms import CursoForm, CategoriaForm
from moderacion.forms import RechazarEmpresaForm
from moderacion.models import SolicitudEmpresa
from ofertas.forms import HabilidadForm
from usuarios.models import Usuario

from ientrabajo.ui_review import SCREENS
from .data import fixtures, DATE

ADMIN_TEMPLATES = {
    'ADM-01': 'moderacion/listar_empresas.html',
    'ADM-02': 'moderacion/detalle_empresa.html',
    'ADM-03': 'moderacion/rechazar_empresa.html',
    'ADM-04': 'moderacion/solicitudes_empresas.html',
    'ADM-05': 'moderacion/ofertas_pendientes.html',
    'ADM-06': 'moderacion/detalle_oferta.html',
    'ADM-07': 'moderacion/rechazar_oferta.html',
    'ADM-08': 'moderacion/listar_cursos.html',
    'ADM-09': 'moderacion/crear_curso.html',
    'ADM-10': 'moderacion/modificar_curso.html',
    'ADM-11': 'moderacion/confirmar_baja.html',
    'ADM-12': 'moderacion/listar_categorias.html',
    'ADM-13': 'moderacion/crear_categoria.html',
    'ADM-14': 'moderacion/modificar_categoria.html',
    'ADM-15': 'moderacion/confirmar_baja_categoria.html',
    'ADM-16': 'moderacion/listar_habilidades.html',
    'ADM-17': 'moderacion/crear_habilidad.html',
    'ADM-18': 'moderacion/modificar_habilidad.html',
    'ADM-19': 'moderacion/confirmar_baja_habilidad.html',
}


def admin_fixtures():
    data = fixtures()
    staff = Usuario(pk=99, email='admin.demo@example.com', first_name='Administración', last_name='IEN', is_staff=True)
    staff._state.fields_cache.update(oferente=None, postulante=None)
    companies = []
    for index, state, name in [(0, 'pendiente', 'Norte Digital'), (1, 'aprobado', 'Empresa del Litoral'), (2, 'rechazado', 'Estudio Regional')]:
        company = copy(data['oferente'])
        company.pk, company.nombre_empresa, company.estado_validacion = index, name, state
        company.usuario = Usuario(pk=index + 10, email=f'empresa{index}@example.com')
        company.motivo_rechazo = 'Revisá los datos de contacto de la empresa.' if state == 'rechazado' else ''
        companies.append(company)
    offers = data['ofertas']
    for offer, state in zip(offers, ('pendiente', 'activa', 'rechazada')):
        offer.estado = state
        offer.requiere_revision_requisitos = False
    data['categoria'].total_habilidades = 2
    skills = [Habilidad(pk=i, categoria=data['categoria'], nombre=name, tipo_habilidad=kind) for i, name, kind in [(0, 'Python', 'D'), (1, 'Trabajo en equipo', 'B')]]
    applications = [SolicitudEmpresa(pk=i, empresa=company, estado=company.estado_validacion, creada_en=DATE, recordar_desde=DATE, resuelta_en=None if i == 0 else DATE) for i, company in enumerate(companies)]
    notifications = {
        'pendientes': 2, 'empresas_pendientes': 1, 'ofertas_pendientes': 1,
        'recientes': [
            {'titulo': companies[0].nombre_empresa, 'tipo': 'Empresa', 'estado': 'Pendiente', 'fecha': DATE.isoformat(), 'url': reverse('mod_detalle_empresa', args=[0])},
            {'titulo': offers[0].titulo, 'tipo': 'Oferta', 'estado': 'Pendiente de aprobación', 'fecha': DATE.isoformat(), 'url': reverse('mod_detalle_oferta', args=[0])},
        ],
    }
    return data, staff, companies, skills, applications, notifications


def admin_screen(request, screen_id):
    data, staff, companies, skills, applications, notifications = admin_fixtures()
    request.user = staff
    screen = next(item for item in SCREENS if item.id == screen_id)
    record_id = request.resolver_match.kwargs.get('pk', request.resolver_match.kwargs.get('curso_id', request.resolver_match.kwargs.get('categoria_id', request.resolver_match.kwargs.get('habilidad_id', 0))))
    company = next((item for item in companies if item.pk == record_id), companies[0])
    offer = next((item for item in data['ofertas'] if item.pk == record_id), data['ofertas'][0])
    course = next((item for item in data['cursos'] if item.pk == record_id), data['cursos'][0])
    skill = next((item for item in skills if item.pk == record_id), skills[0])
    state = request.GET.get('estado', '')
    filtered_offers = [item for item in data['ofertas'] if not state or item.estado == state]
    filtered_applications = [item for item in applications if not state or item.estado == state]
    form = None
    if screen_id == 'ADM-03':
        form = RechazarEmpresaForm()
    elif screen_id in ('ADM-09', 'ADM-10'):
        # Do not give ModelForm a saved-looking PK: it would query the M2M relation.
        form = CursoForm(initial={name: getattr(course, name) for name in ('nombre', 'descripcion', 'duracion', 'horario', 'tipo')} if screen_id == 'ADM-10' else None)
        form.fields['categoria'].choices = [('', 'Seleccionar categoría'), ('0', 'Tecnología')]
        if screen_id == 'ADM-10':
            form.initial['categoria'] = '0'
        form.fields['habilidades'].choices = [(str(item.pk), item.nombre) for item in skills]
    elif screen_id in ('ADM-13', 'ADM-14'):
        form = CategoriaForm(instance=data['categoria'] if screen_id == 'ADM-14' else None)
    elif screen_id in ('ADM-17', 'ADM-18'):
        form = HabilidadForm(instance=skill if screen_id == 'ADM-18' else None)
    context = {
        'user': staff, 'design_demo': True, 'ui_review_preview': True, 'ui_review_screen': screen,
        'admin_review_notifications': notifications, 'form': form,
        'empresas': companies, 'empresa': company, 'oferente': company,
        'ofertas': filtered_offers, 'oferta': offer, 'filtro_actual': state,
        'total': 1 if screen_id == 'ADM-01' else len(data['ofertas']), 'pendientes': 1, 'aprobadas': 1,
        'cursos': data['cursos'], 'curso': course, 'cursos_presenciales': 0, 'cursos_virtuales': len(data['cursos']),
        'categorias': [data['categoria']], 'categoria': data['categoria'], 'habilidades': skills, 'habilidad': skill,
        'habilidades_duras': ['Python', 'Excel'], 'habilidades_blandas': ['Trabajo en equipo'],
        'pagina': Paginator(filtered_applications, 25).get_page(1), 'estado': state, 'reminder_hours': 24,
    }
    return render(request, ADMIN_TEMPLATES[screen_id], context)
