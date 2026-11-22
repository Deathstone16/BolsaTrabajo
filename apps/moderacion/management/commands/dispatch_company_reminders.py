from django.core.management.base import BaseCommand
from moderacion.reminders import enviar_recordatorios_empresas


class Command(BaseCommand):
    help = 'Envía un resumen de solicitudes de empresas vencidas que siguen pendientes.'

    def handle(self, *args, **options):
        count = enviar_recordatorios_empresas()
        self.stdout.write(f'Solicitudes incluidas en el resumen: {count}')
