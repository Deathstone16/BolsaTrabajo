"""Explicit parent destinations; never rely on browser history or referrers."""
from django import template
from django.urls import reverse

register = template.Library()

PARENTS = {
    'buscar_empleo': ('home', 'Volver al inicio'),
    'detalle_oferta': ('buscar_empleo', 'Volver a las ofertas'),
    'cursos:listado': ('home', 'Volver al inicio'),
    'cursos:detalle': ('cursos:listado', 'Volver a los cursos'),
    'perfil_oferente': ('buscar_empleo', 'Volver a las ofertas'),
    'dashboard_empresa': ('home', 'Volver al inicio'),
    'crear_oferta': ('dashboard_empresa', 'Volver a mis ofertas'),
    'editar_oferta': ('dashboard_empresa', 'Volver a mis ofertas'),
    'eliminar_oferta': ('dashboard_empresa', 'Volver a mis ofertas'),
    'editar_perfil_empresa': ('dashboard_empresa', 'Volver a mi empresa'),
    'mi_perfil': ('home', 'Volver al inicio'),
    'perfil_cv': ('home', 'Volver al inicio'),
    'datos_personales': ('ia:perfil_profesional', 'Volver a mi perfil'),
    'favoritos': ('buscar_empleo', 'Volver a las ofertas'),
    'ia:perfil_profesional': ('mi_perfil', 'Volver a mi CV'),
    'ia:ver_resultado': ('mi_perfil', 'Volver a mi CV'),
    'ia:editar_habilidades': ('mi_perfil', 'Volver a mi CV'),
    'mod_solicitudes_empresas': ('mod_listar_empresas', 'Volver a las empresas'),
    'mod_listar_empresas': ('home', 'Volver al inicio'),
    'mod_detalle_empresa': ('mod_listar_empresas', 'Volver a las empresas'),
    'mod_rechazar_empresa': ('mod_listar_empresas', 'Volver a las empresas'),
    'mod_listar_ofertas': ('mod_listar_empresas', 'Volver al panel'),
    'mod_detalle_oferta': ('mod_listar_ofertas', 'Volver a las ofertas'),
    'mod_rechazar_oferta': ('mod_listar_ofertas', 'Volver a las ofertas'),
    'mod_listar_cursos': ('mod_listar_empresas', 'Volver al panel'),
    'mod_crear_curso': ('mod_listar_cursos', 'Volver a los cursos'),
    'mod_modificar_curso': ('mod_listar_cursos', 'Volver a los cursos'),
    'mod_dar_de_baja_curso': ('mod_listar_cursos', 'Volver a los cursos'),
    'mod_listar_categorias': ('mod_listar_empresas', 'Volver al panel'),
    'mod_crear_categoria': ('mod_listar_categorias', 'Volver a las categorías'),
    'mod_modificar_categoria': ('mod_listar_categorias', 'Volver a las categorías'),
    'mod_dar_de_baja_categoria': ('mod_listar_categorias', 'Volver a las categorías'),
    'mod_listar_habilidades': ('mod_listar_categorias', 'Volver a las categorías'),
}


@register.inclusion_tag('nueva_ui/partials/_back_link.html', takes_context=True)
def app_back_link(context):
    request = context.get('request')
    match = getattr(request, 'resolver_match', None)
    screen = context.get('ui_review_screen')
    route = screen.route if screen else (match.view_name if match else '')
    if route in ('mod_crear_habilidad', 'mod_modificar_habilidad', 'mod_eliminar_habilidad'):
        skill = context.get('habilidad')
        category = context.get('categoria')
        category_id = skill.categoria_id if skill else (category.pk if category else None)
        if category_id is not None:
            return {'back_url': reverse('mod_listar_habilidades', args=[category_id]), 'back_label': 'Volver a las habilidades'}
    if route in PARENTS:
        parent, label = PARENTS[route]
        return {'back_url': reverse(parent), 'back_label': label}
    return {}
