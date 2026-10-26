"""Production settings for the Docker web service on Render."""

import os
from hashlib import sha256
from urllib.parse import unquote, urlsplit

os.environ.setdefault('DEBUG', 'false')
os.environ.setdefault('DB_ENGINE', 'postgresql')
database_url = os.environ.get('DATABASE_URL', '').strip()
if database_url:
    parsed_db = urlsplit(database_url)
    if parsed_db.scheme not in {'postgres', 'postgresql'} or not all((
        parsed_db.hostname, parsed_db.username, parsed_db.password, parsed_db.path.lstrip('/'),
    )):
        raise RuntimeError('DATABASE_URL debe ser una URL PostgreSQL completa.')
    os.environ['DB_NAME'] = unquote(parsed_db.path.lstrip('/'))
    os.environ['DB_USER'] = unquote(parsed_db.username)
    os.environ['DB_PASSWORD'] = unquote(parsed_db.password)
    os.environ['DB_HOST'] = parsed_db.hostname
    os.environ['DB_PORT'] = str(parsed_db.port or 5432)
    os.environ['DB_SSLMODE'] = 'require'
if os.environ.get('SECRET_KEY', '').strip():
    # La demo no usa callbacks; satisface la validación de base con un valor
    # privado derivado del secreto de Django, sin otra variable manual.
    os.environ.setdefault('IA_CALLBACK_HMAC_SECRET', sha256(
        ('render-demo-callback:' + os.environ['SECRET_KEY']).encode()
    ).hexdigest())
render_hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if render_hostname:
    os.environ.setdefault('ALLOWED_HOSTS', render_hostname)
    os.environ.setdefault('CSRF_TRUSTED_ORIGINS', f'https://{render_hostname}')

from .base import *  # noqa: F403,E402

if DEBUG:  # noqa: F405
    raise RuntimeError('Render debe ejecutarse con DEBUG=false.')
if not os.environ.get('SECRET_KEY', '').strip():
    raise RuntimeError('Configurá SECRET_KEY en Render antes de iniciar.')

# Este servicio es una demo visual: la API y el escáner de CV no se ejecutan.
# La selección vive solo en este módulo; settings.base conserva su conducta.
CV_SCAN_ENABLED = False
IA_API_URL = ''
IA_OFFER_API_URL = ''
RENDER_UI_DEMO = True
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}

MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
TEMPLATES[0]['OPTIONS']['context_processors'].remove('ia.context_processors.cv_notifications')  # noqa: F405
TEMPLATES[0]['OPTIONS']['context_processors'].append('ientrabajo.render_demo.context')  # noqa: F405
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
ROOT_URLCONF = 'ientrabajo.render_urls'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Render checks this endpoint over its internal HTTP connection.
SECURE_REDIRECT_EXEMPT = [r'^health/?$']
