"""Local, read-only map of the product screens for manual UI reviews."""
from dataclasses import dataclass
from copy import copy
from datetime import timedelta
import re
from urllib.parse import urlencode

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET


@dataclass(frozen=True)
class Screen:
    id: str
    group: str
    title: str
    route: str
    entity: str = ''
    note: str = ''
    query: str = ''
    state: str = ''


SCREENS = (
    Screen('ERR-01', 'Errores', 'Solicitud inválida', 'design_demo_screen'),
    Screen('ERR-02', 'Errores', 'Acceso restringido', 'design_demo_screen'),
    Screen('ERR-03', 'Errores', 'Página no encontrada', 'design_demo_screen'),
    Screen('ERR-04', 'Errores', 'Error del servidor', 'design_demo_screen'),
    Screen('ERR-05', 'Errores', 'Servicio no disponible', 'design_demo_screen'),
    Screen('ERR-06', 'Errores', 'Tiempo de espera', 'design_demo_screen'),
    Screen('ERR-07', 'Errores', 'Sin conexión', 'design_demo_screen'),
    Screen('PUB-01', 'Público', 'Landing', 'home', note='Revisar menú mobile, ofertas, cursos, filtros y footer.'),
    Screen('PUB-02', 'Público', 'Buscar empleo', 'buscar_empleo', note='Buscar por título, empresa, habilidad y localidad; probar sin resultados.'),
    Screen('PUB-03', 'Público', 'Detalle de oferta', 'detalle_oferta', 'oferta_publica', 'Revisar también con sesión de postulante: favoritos y compatibilidad.'),
    Screen('PUB-04', 'Público', 'Catálogo de cursos', 'cursos:listado', note='Combinar filtros y revisar paginación y resultados vacíos.'),
    Screen('PUB-05', 'Público', 'Detalle de curso', 'cursos:detalle', 'curso_publico'),
    Screen('PUB-06', 'Postulante', 'Perfil público de empresa', 'perfil_oferente', 'empresa_publica'),
    Screen('ACC-01', 'Acceso', 'Inicio de sesión', 'login', note='Probar campos vacíos, credenciales incorrectas y mostrar contraseña.'),
    Screen('ACC-02', 'Acceso', 'Registro de postulante', 'registro', query='postulante', note='Probar validaciones y confirmación de contraseña.'),
    Screen('ACC-03', 'Acceso', 'Registro exitoso de postulante', 'registro_exitoso'),
    Screen('ACC-04', 'Acceso', 'Recuperar contraseña', 'recuperar-contrasena'),
    Screen('ACC-05', 'Acceso', 'Enlace de recuperación enviado', 'recuperacion-enviada'),
    Screen('ACC-06', 'Acceso', 'Nueva contraseña / enlace vencido', 'restablecer-contrasena', 'reset', 'La nueva contraseña se abre desde un enlace válido recibido por email. El acceso de esta lista muestra el estado de enlace inválido.'),
    Screen('ACC-07', 'Acceso', 'Contraseña actualizada', 'contrasena-restablecida'),
    Screen('POS-01', 'Postulante', 'Mi CV y análisis', 'mi_perfil', note='Revisar sin CV, con CV, análisis en curso, terminado y error; menú del archivo y foto.'),
    Screen('POS-02', 'Postulante', 'Perfil profesional', 'ia:perfil_profesional', note='Completar primero un análisis para ver todas las secciones.'),
    Screen('POS-03', 'Postulante', 'Editar perfil profesional', 'ia:editar_perfil_cv', note='Necesita un perfil generado por el análisis del CV.'),
    Screen('POS-04', 'Postulante', 'Resultado del análisis', 'ia:ver_resultado', 'analisis', 'Necesita un análisis de tu propio CV.'),
    Screen('POS-05', 'Postulante', 'Revisar habilidades del análisis', 'ia:editar_habilidades', 'analisis'),
    Screen('POS-06', 'Postulante', 'Mis datos personales', 'datos_personales'),
    Screen('POS-07', 'Postulante', 'Datos guardados', 'datos_personales_exitoso'),
    Screen('POS-08', 'Postulante', 'Favoritos', 'favoritos', note='Revisar con ofertas guardadas y lista vacía.'),
    Screen('POS-09', 'Postulante', 'Detalle de compatibilidad', 'matching:detalle', 'match', 'Calcular primero una compatibilidad desde el detalle de una oferta.'),
    Screen('EMP-01', 'Acceso', 'Registro de empresa', 'registro', query='oferente'),
    Screen('EMP-02', 'Acceso', 'Empresa registrada en revisión', 'registro_exitoso', query='oferente'),
    Screen('EMP-03', 'Empresa', 'Empresa pendiente', 'validacion_pendiente', state='pendiente'),
    Screen('EMP-04', 'Empresa', 'Empresa aprobada', 'validacion_pendiente', state='aprobado'),
    Screen('EMP-05', 'Empresa', 'Empresa rechazada', 'validacion_pendiente', state='rechazado'),
    Screen('EMP-06', 'Empresa', 'Mis ofertas', 'dashboard_empresa', note='Necesita empresa aprobada y responsable completo. Revisar las dos pestañas y los diálogos.'),
    Screen('EMP-07', 'Empresa', 'Editar mi empresa', 'editar_perfil_empresa', note='Revisar campos obligatorios, logo, portada, recorte y sitio web.'),
    Screen('EMP-08', 'Empresa', 'Publicar oferta', 'crear_oferta', note='Necesita empresa aprobada. Revisar errores, requisitos, clasificación y confidencialidad.'),
    Screen('EMP-09', 'Empresa', 'Editar oferta propia', 'editar_oferta', 'oferta_propia'),
    Screen('EMP-10', 'Empresa', 'Confirmar eliminación de oferta', 'eliminar_oferta', 'oferta_propia', 'Abrir la confirmación no elimina la oferta.'),
    Screen('ADM-01', 'Administración', 'Validación de empresas', 'mod_listar_empresas', note='Revisar todos los estados, búsqueda por CUIT y tarjetas mobile.'),
    Screen('ADM-02', 'Administración', 'Detalle de empresa', 'mod_detalle_empresa', 'empresa_admin', 'Revisar empresas pendientes, aprobadas y rechazadas.'),
    Screen('ADM-03', 'Administración', 'Rechazar empresa', 'mod_rechazar_empresa', 'empresa_pendiente'),
    Screen('ADM-04', 'Administración', 'Historial de solicitudes', 'mod_solicitudes_empresas', note='Revisar filtros por estado y campana del header.'),
    Screen('ADM-05', 'Administración', 'Gestión de ofertas', 'mod_listar_ofertas'),
    Screen('ADM-06', 'Administración', 'Detalle de oferta', 'mod_detalle_oferta', 'oferta_admin'),
    Screen('ADM-07', 'Administración', 'Rechazar oferta', 'mod_rechazar_oferta', 'oferta_pendiente'),
    Screen('ADM-08', 'Administración', 'Gestión de cursos', 'mod_listar_cursos'),
    Screen('ADM-09', 'Administración', 'Crear curso', 'mod_crear_curso'),
    Screen('ADM-10', 'Administración', 'Editar curso', 'mod_modificar_curso', 'curso_admin'),
    Screen('ADM-11', 'Administración', 'Confirmar baja de curso', 'mod_dar_de_baja_curso', 'curso_admin'),
    Screen('ADM-12', 'Administración', 'Categorías y habilidades', 'mod_listar_categorias'),
    Screen('ADM-13', 'Administración', 'Crear categoría', 'mod_crear_categoria'),
    Screen('ADM-14', 'Administración', 'Editar categoría', 'mod_modificar_categoria', 'categoria'),
    Screen('ADM-15', 'Administración', 'Confirmar baja de categoría', 'mod_dar_de_baja_categoria', 'categoria'),
    Screen('ADM-16', 'Administración', 'Habilidades de una categoría', 'mod_listar_habilidades', 'categoria'),
    Screen('ADM-17', 'Administración', 'Crear habilidad', 'mod_crear_habilidad', 'categoria'),
    Screen('ADM-18', 'Administración', 'Editar habilidad', 'mod_modificar_habilidad', 'habilidad'),
    Screen('ADM-19', 'Administración', 'Confirmar baja de habilidad', 'mod_eliminar_habilidad', 'habilidad'),
)

COMPANY_PREVIEWS = {
    'PUB-06': 'Ofertas/perfil_oferente_publico.html',
    **{f'EMP-0{i}': 'Ofertas/validacion_pendiente.html' for i in (3, 4, 5)},
    'EMP-06': 'Ofertas/home_oferente.html',
    'EMP-07': 'Ofertas/editar-perfil.html',
    'EMP-08': 'Ofertas/crear-empleo.html',
    'EMP-09': 'Ofertas/editar-empleo.html',
    'EMP-10': 'Ofertas/confirmar-eliminar-oferta.html',
}


@require_GET
def company_preview(request, screen_id):
    """Render real templates with unsaved fixtures; never bypass real view guards."""
    if not (settings.DEBUG or getattr(settings, 'FRONTEND_DEMO', False)) or screen_id not in COMPANY_PREVIEWS:
        raise Http404
    from django.utils import timezone
    from ofertas.forms import OfertaForm
    from ofertas.models import Oferta
    from usuarios.forms import OferenteForm
    from usuarios.models import Usuario, Oferente

    preview_request = copy(request)
    preview_request.user = Usuario(pk=0, email='empresa@example.com', first_name='Empresa de prueba')
    company = Oferente(
        pk=0, usuario=preview_request.user, nombre_empresa='Empresa de prueba',
        cuit='30712345671', estado_validacion={'EMP-03': 'pendiente', 'EMP-05': 'rechazado'}.get(screen_id, 'aprobado'),
        contacto_nombre='Alex Pérez', contacto_cargo='Recursos Humanos',
        correo_publico='contacto@example.com', telefono='362 400 0000',
        ubicacion='Resistencia, Chaco', industria='Tecnología', tamano_empresa='11-50',
        descripcion='Empresa ficticia para revisar las pantallas de gestión y publicación de ofertas.',
        motivo_rechazo='Revisá los datos de la empresa y completá la documentación solicitada.',
    )
    offer = Oferta(
        pk=0, empresa=preview_request.user, titulo='Analista de datos', nombre_puesto='Analista de datos',
        ubicacion='Resistencia, Chaco', modalidad='hibrido', estado='pendiente',
        descripcion='Buscamos una persona para analizar información y preparar reportes junto al equipo.',
        requisitos_obligatorios='' if screen_id == 'EMP-09' else 'Python\nExcel',
        requisitos_deseables='' if screen_id == 'EMP-09' else 'Trabajo en equipo',
        requiere_revision_requisitos=False if screen_id == 'EMP-09' else True,
        nivel_educativo='terciario', fecha_cierre=timezone.now() + timedelta(days=30),
    )
    screen = next(screen for screen in SCREENS if screen.id == screen_id)
    context = {
        'user': preview_request.user, 'oferente': company, 'oferta': offer, 'ofertas': [offer],
        'form': OferenteForm(instance=company) if screen_id == 'EMP-07' else OfertaForm(instance=offer) if screen_id == 'EMP-09' else OfertaForm(),
        'form_perfil': OferenteForm(instance=company), 'experiencia_choices': Oferta.EXPERIENCIA_CHOICES,
        'ui_review_screen': screen, 'ui_review_preview': True,
    }
    if getattr(settings, 'FRONTEND_DEMO', False):
        for form_name in ('form', 'form_perfil'):
            if 'categoria' in context[form_name].fields:
                context[form_name].fields['categoria'].choices = [('', 'Seleccionar categoría'), ('0', 'Tecnología')]
        context['design_demo'] = True
    response = render(preview_request, COMPANY_PREVIEWS[screen_id], context)
    html = response.content.decode(response.charset)
    # Keep the company navigation inside the preview, including the sample offer.
    for item in SCREENS:
        if item.id not in COMPANY_PREVIEWS or item.state:
            continue
        source = reverse(item.route, args=[0] if item.entity else [])
        target = reverse('ui_review_company', args=[item.id])
        html = html.replace(f'href="{source}"', f'href="{target}"').replace(f'href="{source}#', f'href="{target}#')
    status_url = reverse('validacion_pendiente')
    html = html.replace(f'href="{status_url}"', f'href="{reverse("ui_review_company", args=[screen_id if screen.state else "EMP-03"])}"')
    html = re.sub(r'(<form\b[^>]*\baction=)["\'][^"\']*["\']', lambda match: match[1] + '"' + request.path + '"', html, flags=re.I)
    response.content = html
    # No form submission or AJAX from previews can reach real write endpoints.
    response['Content-Security-Policy'] = "form-action 'none'; connect-src 'none'"
    response['Cache-Control'] = 'no-store'
    return response


def current_screen(request):
    """Resolve the ID without loading the catalog or querying sample records."""
    if not settings.DEBUG:
        return {}
    match = getattr(request, 'resolver_match', None)
    if not match:
        return {}
    for screen in SCREENS:
        if screen.route != {'perfil_cv': 'mi_perfil'}.get(match.view_name, match.view_name):
            continue
        if screen.route in ('registro', 'registro_exitoso'):
            tipo = request.GET.get('tipo', 'postulante')
            if (screen.query or 'postulante') != tipo:
                continue
        if screen.state and screen.state != getattr(getattr(request.user, 'oferente', None), 'estado_validacion', ''):
            continue
        return {'ui_review_screen': screen}
    return {}


def _entities(request):
    from cursos.models import Curso
    from ofertas.models import Oferta
    from usuarios.models import Oferente
    from categorias.models import Categoria, Habilidad
    user = request.user
    entities = {
        'oferta_publica': Oferta.objects.filter(estado='activa').order_by('pk').values_list('pk', flat=True).first(),
        'curso_publico': Curso.objects.filter(activo=True).order_by('pk').values_list('pk', flat=True).first(),
        'reset': ['invalid', 'invalid'],
    }
    if user.is_authenticated and hasattr(user, 'postulante'):
        entities['empresa_publica'] = Oferente.objects.aprobados().order_by('pk').values_list('pk', flat=True).first()
        entities['analisis'] = user.postulante.analisis_cv.order_by('-pk').values_list('pk', flat=True).first()
        entities['match'] = user.postulante.resultados_match.filter(estado='completed').order_by('-pk').values_list('request_id', flat=True).first()
    if user.is_authenticated and hasattr(user, 'oferente'):
        entities['oferta_propia'] = Oferta.objects.filter(empresa=user).order_by('-pk').values_list('pk', flat=True).first()
    if user.is_authenticated and user.is_staff:
        entities['empresa_pendiente'] = Oferente.objects.filter(estado_validacion='pendiente').order_by('pk').values_list('pk', flat=True).first()
        entities['oferta_pendiente'] = Oferta.objects.filter(estado='pendiente').order_by('pk').values_list('pk', flat=True).first()
        for key, model in (('empresa_admin', Oferente), ('oferta_admin', Oferta), ('curso_admin', Curso), ('categoria', Categoria), ('habilidad', Habilidad)):
            entities[key] = model.objects.order_by('pk').values_list('pk', flat=True).first()
    return entities


@require_GET
def screen_index(request):
    if not settings.DEBUG:
        raise Http404
    entities = _entities(request)
    user = request.user
    role = 'Visitante'
    if user.is_authenticated:
        role = 'Administración' if user.is_staff else 'Empresa' if hasattr(user, 'oferente') else 'Postulante' if hasattr(user, 'postulante') else 'Cuenta sin perfil'
    groups = []
    for group in ('Público', 'Acceso', 'Postulante', 'Empresa', 'Administración'):
        items = []
        for screen in SCREENS:
            if screen.group != group:
                continue
            available = group in ('Público', 'Acceso') or role == group
            reason = '' if available else f'Iniciá sesión como {group.lower()}.'
            value = entities.get(screen.entity)
            if screen.entity and not value:
                available = False
                reason = reason or 'Primero necesitás un registro propio o disponible de este tipo.'
            if screen.state and role == 'Empresa' and user.oferente.estado_validacion != screen.state:
                available = False
                reason = f'Necesita una empresa con estado {screen.state}.'
            if role == 'Empresa' and screen.id in ('EMP-04', 'EMP-06', 'EMP-08', 'EMP-09', 'EMP-10') and not user.oferente.puede_publicar:
                available = False
                reason = 'Necesita empresa aprobada y datos del responsable completos.'
            args = value if isinstance(value, list) else [value] if screen.entity else []
            url = reverse(screen.route, args=args) if available else ''
            if url and screen.query:
                url += '?' + urlencode({'tipo': screen.query})
            preview_url = reverse('ui_review_company', args=[screen.id]) if screen.id in COMPANY_PREVIEWS else ''
            items.append({'screen': screen, 'url': url, 'reason': reason, 'preview_url': preview_url})
        groups.append({'title': group, 'items': items})
    return render(request, 'nueva_ui/screen_index.html', {'screen_groups': groups, 'review_role': role, 'screen_count': len(SCREENS)})
