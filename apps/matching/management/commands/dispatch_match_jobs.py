"""Envía solicitudes de match al microservicio por WebSocket servidor a servidor."""

from __future__ import annotations

import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from websockets.sync.client import connect

from ia.models import EventoSalida
from matching.models import ResultadoCompatibilidad
from matching.services import complete_match, match_request_payload, update_match_status


class Command(BaseCommand):
    help = 'Despacha solicitudes pendientes de compatibilidad al matcher Jev.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')
        parser.add_argument('--limit', type=int, default=20)

    def handle(self, *args, **options):
        processed = 0
        while processed < options['limit']:
            event = self._claim()
            if event is None:
                break
            self._send(event)
            processed += 1
            if options['once']:
                break
        self.stdout.write(self.style.SUCCESS(f'Matches procesados: {processed}'))

    def _claim(self):
        with transaction.atomic():
            event = EventoSalida.objects.select_for_update().filter(
                tipo=EventoSalida.Tipo.MATCH,
                estado=EventoSalida.Estado.PENDIENTE,
            ).filter(Q(proximo_intento_en__isnull=True) | Q(proximo_intento_en__lte=timezone.now())).order_by('creado_en').first()
            if event:
                event.estado = EventoSalida.Estado.ENVIANDO
                event.intentos += 1
                event.save(update_fields=['estado', 'intentos', 'actualizado_en'])
            return event

    def _send(self, event):
        match = ResultadoCompatibilidad.objects.select_related('postulante__perfil_ia', 'oferta__perfil_ia').get(pk=event.payload['match_id'])
        try:
            headers = {'Authorization': f'Bearer {settings.MATCH_API_TOKEN}'}
            with connect(settings.MATCH_API_URL, additional_headers=headers, open_timeout=10, close_timeout=5) as socket:
                socket.send(json.dumps({'type': 'match.start', 'payload': match_request_payload(match)}))
                while True:
                    message = json.loads(socket.recv(timeout=60))
                    status = message.get('status')
                    if status in {'accepted', 'processing', 'rate_limited'}:
                        update_match_status(str(match.request_id), status)
                        continue
                    if status == 'completed':
                        complete_match(str(match.request_id), message['result'])
                        event.estado = EventoSalida.Estado.ENVIADO
                        event.error = ''
                        event.save(update_fields=['estado', 'error', 'actualizado_en'])
                        return
                    if status == 'failed':
                        update_match_status(str(match.request_id), 'failed', message.get('error', 'El matcher devolvió un error.'))
                        event.estado = EventoSalida.Estado.ERROR
                        event.error = 'El matcher devolvió un error.'
                        event.save(update_fields=['estado', 'error', 'actualizado_en'])
                        return
        except Exception:
            event.estado = EventoSalida.Estado.PENDIENTE
            event.error = 'No se pudo entregar el match al microservicio.'
            event.proximo_intento_en = timezone.now() + timedelta(seconds=min(300, 2 ** min(event.intentos, 8)))
            event.save(update_fields=['estado', 'error', 'proximo_intento_en', 'actualizado_en'])
