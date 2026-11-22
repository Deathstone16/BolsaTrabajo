"""Standalone frontend demo; deliberately does not import production settings."""
import os
import sys
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / 'apps'))
DEBUG = False
FRONTEND_DEMO = True
SECRET_KEY = os.environ.get('SECRET_KEY', '')
if not SECRET_KEY:
    raise ImproperlyConfigured('Configurá SECRET_KEY para la demo de diseño.')
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost,127.0.0.1')).split(',') if host.strip()]
ROOT_URLCONF = 'ientrabajo.design_demo.urls'
ASGI_APPLICATION = 'ientrabajo.design_demo.asgi.application'
AUTH_USER_MODEL = 'usuarios.Usuario'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
INSTALLED_APPS = [
    'daphne', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'usuarios', 'cursos', 'moderacion', 'ofertas', 'categorias', 'emails', 'ia', 'matching', 'channels',
]
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'ientrabajo.design_demo.middleware.DesignDemoMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
            'ientrabajo.context_processors.contacto_ien',
        ],
        'builtins': ['ientrabajo.templatetags.ien_static', 'ientrabajo.templatetags.ien_navigation'],
    },
}]
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_TZ = True
USE_I18N = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}}
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
