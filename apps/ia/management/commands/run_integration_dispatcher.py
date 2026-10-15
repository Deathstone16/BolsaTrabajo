"""Despachador continuo para desarrollo y procesos supervisados."""

import time

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import close_old_connections


class Command(BaseCommand):
    help = 'Entrega continuamente trabajos de extracción o compatibilidad.'

    def add_arguments(self, parser):
        parser.add_argument('--kind', choices=['extraction', 'match'], required=True)
        parser.add_argument('--interval', type=float, default=2)

    def handle(self, *args, **options):
        command = 'dispatch_match_jobs' if options['kind'] == 'match' else 'dispatch_integration_outbox'
        try:
            while True:
                close_old_connections()
                call_command(command, limit=20, stdout=self.stdout, stderr=self.stderr)
                time.sleep(max(0.1, options['interval']))
        except KeyboardInterrupt:
            self.stdout.write('Despachador detenido.')
