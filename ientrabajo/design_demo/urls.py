"""Only frontend URL names, all intercepted by the read-only demo middleware."""
from functools import partial
from django.contrib.staticfiles.views import serve
from django.urls import include, path, re_path
from ientrabajo.ui_review import screen_index, company_preview
from usuarios.views import mi_perfil
from . import views

urlpatterns = [
    path('', views.screen, {'screen_id': 'PUB-01'}, name='home'),
    path('demo/<str:screen_id>/', views.screen, name='design_demo_screen'),
    path('demo-cv/', views.cv, name='design_demo_cv'),
    path('health/', views.health, name='design_demo_health'),
    path('revision-ui/', views.index, name='ui_review'),
    path('revision-ui/empresa/<str:screen_id>/', company_preview, name='ui_review_company'),
    path('usuarios/', include('usuarios.urls')),
    path('perfil/', mi_perfil, name='perfil_cv'),
    path('ofertas/', include('ofertas.urls')),
    path('cursos/', include('cursos.urls')),
    path('ia/', include('ia.urls')),
    path('matching/', include('matching.urls')),
    path('moderacion/', include('moderacion.urls')),
    re_path(r'^static/(?P<path>.*)$', partial(serve, insecure=True)),
]

handler400 = 'ientrabajo.error_pages.bad_request'
handler403 = 'ientrabajo.error_pages.permission_denied'
handler404 = 'ientrabajo.error_pages.not_found'
handler500 = 'ientrabajo.error_pages.server_error'
