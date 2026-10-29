"""Collectstatic dentro de Docker: no necesita servicios ni secretos reales."""

from .base import *  # noqa: F403

DEBUG = False
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
