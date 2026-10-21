"""Datos públicos de contacto compartidos por las pantallas del sitio."""
from django.conf import settings
from urllib.parse import urlencode


def contacto_ien(request):
    email = getattr(settings, 'IEN_CONTACT_EMAIL', '').strip()
    url = f"mailto:{email}?{urlencode({'subject': 'Consulta a IEN Trabajo'})}" if email else ''
    return {'ien_contact_email': email, 'ien_contact_url': url}
