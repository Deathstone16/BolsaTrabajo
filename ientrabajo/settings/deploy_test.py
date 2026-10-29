"""Verificación aislada: nunca usa la base, los CV o el correo del desarrollador."""

import os

os.environ.update(DEBUG='true', DB_ENGINE='sqlite', DATABASE_URL='', PYTHON_DOTENV_DISABLED='1')

from .base import *  # noqa: F403, E402

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
MEDIA_ROOT = BASE_DIR / '.test-artifacts' / 'deploy-media'
PRIVATE_CV_ROOT = BASE_DIR / '.test-artifacts' / 'deploy-private'
STATIC_ROOT = BASE_DIR / '.test-artifacts' / 'deploy-static'
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
CV_SCAN_ENABLED = False
CV_LEGACY_CONVERTER_IMAGE = ''
