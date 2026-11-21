from django.http import HttpResponseNotAllowed, HttpResponseNotFound
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
        if request.method not in ('GET', 'HEAD'):
            return HttpResponseNotAllowed(['GET', 'HEAD'])
        if request.path.startswith('/static/') or view in (views.health, views.cv):
            return None
        name = request.resolver_match.view_name
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
