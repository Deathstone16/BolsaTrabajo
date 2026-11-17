from django.apps import AppConfig


class ModeracionConfig(AppConfig):
    name = 'moderacion'

    def ready(self):
        from . import signals  # noqa: F401
