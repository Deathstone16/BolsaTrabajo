from django.http import HttpResponseNotAllowed, HttpResponseNotFound
from django.shortcuts import redirect
from ientrabajo.ui_review import SCREENS, COMPANY_PREVIEWS
from . import views


class DesignDemoMiddleware:
    """Every application request is intercepted before auth, ORM or side effects."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Cache-Control'] = 'no-store' if not request.path.startswith('/static/') else 'public, max-age=3600'
        response['Content-Security-Policy'] = "form-action 'self'; connect-src 'none'; object-src 'none'; base-uri 'self'"
        return response

    def process_view(self, request, view, args, kwargs):
        # A no-JavaScript fallback for the demo profile's "view example" button.
        # Do not read POST values or invoke the real profile/analysis services.
        if request.method == 'POST' and (
            request.resolver_match.view_name == 'ia:editar_perfil_cv'
            or request.resolver_match.view_name == 'design_demo_screen' and kwargs.get('screen_id') == 'POS-03'
        ):
            return redirect('design_demo_screen', screen_id='POS-04')
        if request.method not in ('GET', 'HEAD'):
            return HttpResponseNotAllowed(['GET', 'HEAD'])
        if request.path.startswith('/static/') or view in (views.health, views.cv):
            return None
        name = request.resolver_match.view_name
        if name == 'mod_notificaciones_admin':
            from django.http import JsonResponse
            from .admin_views import admin_fixtures
            return JsonResponse(admin_fixtures()[-1])
        if name == 'ui_review':
            return views.index(request)
        if name in ('ui_review_company', 'design_demo_screen'):
            return views.screen(request, kwargs['screen_id'])
        if name == 'descargar_cv':
            return views.cv(request)
        aliases = {'perfil_cv': 'mi_perfil', 'logout': 'login'}
        name = aliases.get(name, name)
        for item in SCREENS:
            if item.route != name:
                continue
            if item.query and item.query != request.GET.get('tipo', 'postulante'):
                continue
            if item.id in views.TEMPLATES or item.id in COMPANY_PREVIEWS:
                return views.screen(request, item.id)
        return HttpResponseNotFound('Esta acción no está disponible en la demo de diseño.')
