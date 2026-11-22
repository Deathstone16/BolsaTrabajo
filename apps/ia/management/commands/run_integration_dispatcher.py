"""Despachador continuo para desarrollo y procesos supervisados."""

import time

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import close_old_connections


class Command(BaseCommand):
    help = 'Entrega continuamente trabajos de extracción o compatibilidad.'

    def add_arguments(self, parser):
        parser.add_argument('--kind', choices=['extraction', 'match', 'company-reminders'], required=True)
        parser.add_argument('--interval', type=float, default=2)

    def handle(self, *args, **options):
        command = {
            'match': 'dispatch_match_jobs',
            'extraction': 'dispatch_integration_outbox',
            'company-reminders': 'dispatch_company_reminders',
        }[options['kind']]
        try:
            while True:
                close_old_connections()
                kwargs = {} if options['kind'] == 'company-reminders' else {'limit': 20}
                call_command(command, stdout=self.stdout, stderr=self.stderr, **kwargs)
                time.sleep(max(0.1, options['interval']))
        except KeyboardInterrupt:
            self.stdout.write('Despachador detenido.')
