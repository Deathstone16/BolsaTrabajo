"""Tag {% static_v %}: como {% static %}, pero con la version del archivo en la URL.

Agrega ?v=<fecha de modificacion> a la URL del archivo estatico. Cuando el
archivo cambia, cambia la URL y el navegador baja la version nueva en vez de
usar la que tenia cacheada (antes habia que hacer Ctrl+F5 a mano).

Esta registrado como builtin en TEMPLATES (settings/base.py), asi que se usa
en cualquier plantilla sin {% load %}:

    <script src="{% static_v 'js/ui/ien-ui.js' %}"></script>
"""
import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_v(ruta):
    url = static(ruta)
    archivo = finders.find(ruta)
    if not archivo:
        return url
    version = int(os.path.getmtime(archivo))
    return '%s%sv=%d' % (url, '&' if '?' in url else '?', version)
