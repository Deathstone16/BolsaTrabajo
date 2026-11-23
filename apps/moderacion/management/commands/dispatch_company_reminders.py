from django.core.management.base import BaseCommand
from moderacion.reminders import enviar_recordatorios_empresas


class Command(BaseCommand):
    help = 'Reintenta avisos de validación de empresas pendientes que no se enviaron.'

    def handle(self, *args, **options):
        count = enviar_recordatorios_empresas()
        self.stdout.write(f'Solicitudes notificadas: {count}')
