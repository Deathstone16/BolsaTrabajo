"""Despacha eventos de extracción sin bloquear los requests web."""

from __future__ import annotations

from datetime import timedelta

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ia.models import EventoSalida, TrabajoExtraccion
from ia.workflow import offer_snapshot


class Command(BaseCommand):
    help = 'Envía al extractor los trabajos pendientes de CV y ofertas.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')
        parser.add_argument('--limit', type=int, default=20)

    def handle(self, *args, **options):
        processed = 0
        while processed < options['limit']:
            event = self._claim_next()
            if event is None:
                break
            self._dispatch(event)
            processed += 1
            if options['once']:
                break
        self.stdout.write(self.style.SUCCESS(f'Eventos procesados: {processed}'))

    def _claim_next(self):
        with transaction.atomic():
            event = EventoSalida.objects.select_for_update().filter(
                tipo__in=[
                    EventoSalida.Tipo.EXTRAER_CV,
                    EventoSalida.Tipo.EXTRAER_OFERTA,
                    EventoSalida.Tipo.NORMALIZAR_PERFIL,
                ],
                estado=EventoSalida.Estado.PENDIENTE,
            ).filter(Q(proximo_intento_en__isnull=True) | Q(proximo_intento_en__lte=timezone.now())).order_by('creado_en').first()
            if event:
                event.estado = EventoSalida.Estado.ENVIANDO
                event.intentos += 1
                event.save(update_fields=['estado', 'intentos', 'actualizado_en'])
            return event

    def _dispatch(self, event):
        job = TrabajoExtraccion.objects.select_related('analisis_cv__postulante', 'oferta').get(pk=event.payload['job_id'])
        try:
            headers = {
                'Authorization': f'Bearer {settings.IA_API_TOKEN}',
                'Idempotency-Key': job.clave_idempotencia,
            }
            if job.tipo == TrabajoExtraccion.Tipo.CV:
                analysis = job.analisis_cv
                cv_source = job.cv_snapshot or analysis.postulante.cv
                with cv_source.open('rb') as cv_file:
                    response = requests.post(
                        settings.IA_API_URL,
                        headers=headers,
                        data={'analysis_id': analysis.pk, 'candidate_id': analysis.postulante_id},
                        files={'cv': (cv_source.name.rsplit('/', 1)[-1], cv_file, 'application/pdf')},
                        timeout=20,
                    )
            elif job.tipo == TrabajoExtraccion.Tipo.OFERTA:
                response = requests.post(
                    settings.IA_OFFER_API_URL or settings.IA_API_URL.replace('/cv-analyses', '/offer-analyses'),
                    headers=headers,
                    json={'offer_id': job.oferta_id, 'source_hash': job.source_hash, 'offer_snapshot': offer_snapshot(job.oferta)},
                    timeout=20,
                )
            else:
                response = requests.post(
                    settings.IA_API_URL.replace('/cv-analyses', '/profile-normalizations'),
                    headers=headers,
                    json={
                        'candidate_id': int(job.profile_snapshot['profile_id']),
                        'source_hash': job.source_hash,
                        'profile_snapshot': job.profile_snapshot,
                    },
                    timeout=20,
                )
            response.raise_for_status()
            body = response.json()
            job.remote_job_id = body['job_id']
            job.estado = TrabajoExtraccion.Estado.ACEPTADO
            job.save(update_fields=['remote_job_id', 'estado', 'actualizado_en'])
            event.estado = EventoSalida.Estado.ENVIADO
            event.error = ''
            event.save(update_fields=['estado', 'error', 'actualizado_en'])
        except (OSError, requests.RequestException, ValueError, KeyError) as exc:
            event.estado = EventoSalida.Estado.PENDIENTE
            event.error = 'No se pudo entregar el trabajo al extractor.'
            event.proximo_intento_en = timezone.now() + timedelta(seconds=min(300, 2 ** min(event.intentos, 8)))
            event.save(update_fields=['estado', 'error', 'proximo_intento_en', 'actualizado_en'])
