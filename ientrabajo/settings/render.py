"""Perfil académico Render Free + Neon. Los archivos no usan el disco efímero."""

import os
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

# Render entrega el hostname real, incluso si agregó un sufijo al nombre elegido.
hostname = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if hostname:
    hosts = [item for item in os.environ.get('ALLOWED_HOSTS', '').split(',') if item]
    origins = [item for item in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if item]
    os.environ['ALLOWED_HOSTS'] = ','.join(dict.fromkeys([*hosts, hostname]))
    os.environ['CSRF_TRUSTED_ORIGINS'] = ','.join(dict.fromkeys([*origins, f'https://{hostname}']))

from .base import *  # noqa: F403, E402

if DEBUG:
    raise ImproperlyConfigured('El despliegue requiere DEBUG=false.')

required = ('AWS_STORAGE_BUCKET_NAME', 'AWS_ENDPOINT_URL_S3', 'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY', 'AWS_REGION', 'CHANNEL_REDIS_URL', 'MATCH_CACHE_REDIS_URL',
            'IA_API_URL', 'IA_OFFER_API_URL', 'IA_API_TOKEN', 'MATCH_API_URL',
            'MATCH_API_HTTP_URL', 'MATCH_API_TOKEN')
missing = [name for name in required if not os.environ.get(name)]
if missing:
    raise ImproperlyConfigured('Faltan variables de despliegue: ' + ', '.join(missing))
if urlsplit(os.environ['AWS_ENDPOINT_URL_S3']).scheme != 'https':
    raise ImproperlyConfigured('El almacén de archivos debe usar HTTPS.')
for name, scheme in (('IA_API_URL', 'https'), ('IA_OFFER_API_URL', 'https'),
                     ('MATCH_API_HTTP_URL', 'https'), ('MATCH_API_URL', 'wss')):
    url = urlsplit(os.environ[name])
    if url.scheme != scheme or not url.hostname:
        raise ImproperlyConfigured(f'{name} debe usar {scheme} y el hostname del túnel.')
if IA_API_TOKEN != MATCH_API_TOKEN:
    raise ImproperlyConfigured('La API compartida requiere IA_API_TOKEN y MATCH_API_TOKEN iguales.')

MIDDLEWARE = [MIDDLEWARE[0], 'whitenoise.middleware.WhiteNoiseMiddleware', *MIDDLEWARE[1:]]
SECURE_REDIRECT_EXEMPT = [r'^health/?$']

# Un bucket privado, dos prefijos separados. Ninguna ACL pública se envía a Neon.
storage_options = {
    'bucket_name': os.environ['AWS_STORAGE_BUCKET_NAME'],
    'endpoint_url': os.environ['AWS_ENDPOINT_URL_S3'],
    'access_key': os.environ['AWS_ACCESS_KEY_ID'],
    'secret_key': os.environ['AWS_SECRET_ACCESS_KEY'],
    'region_name': os.environ['AWS_REGION'],
    'addressing_style': 'path',
    'signature_version': 's3v4',
    'default_acl': None,
    'querystring_auth': True,
    'querystring_expire': 3600,
    'file_overwrite': False,
    'max_memory_size': 1024 * 1024,
}
STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {**storage_options, 'location': 'media'},
    },
    'private_cv': {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {**storage_options, 'location': 'private/cv'},
    },
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
