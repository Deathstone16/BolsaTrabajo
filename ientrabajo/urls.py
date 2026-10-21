"""
URL configuration for ientrabajo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound
from django.urls import re_path


def deny_private_media(request, path=''):
    return HttpResponseNotFound()
from . import views
from usuarios.views import mi_perfil


urlpatterns = [
    re_path(r'^media/(?:postulantes/cv|ia/extraction_snapshots)/.*$', deny_private_media),
    path('admin/', admin.site.urls),
    path('',views.home,name='home'),
    path('usuarios/', include('usuarios.urls')),
    path('perfil/', mi_perfil, name='perfil_cv'),
    path('moderacion/', include('moderacion.urls')),
    path('ofertas/', include('ofertas.urls')),
    path('cursos/', include('cursos.urls')),
    path('ia/', include('ia.urls')),
    path('matching/', include('matching.urls')),

    # Ruta temporal: no ejecuta análisis ni llama a Groq.
    path('prueba/', RedirectView.as_view(pattern_name='home', permanent=False), name='ia'),

]

# En producción, los archivos subidos deben servirlos el servidor web/CDN.
# Django solo los expone directamente durante el desarrollo.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
