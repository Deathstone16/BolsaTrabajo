"""Ensure a CV job owns its delivery event, including after historical cleanup."""
from .models import EventoSalida


def ensure_cv_dispatch_event(job):
    # Preserve an existing valid event: accepted/in-flight jobs must not be
    # published twice when the candidate presses the button again.
    legacy = EventoSalida.objects.filter(
        clave_idempotencia=f'outbox:{job.clave_idempotencia}',
    ).first()
    if (legacy is not None and legacy.tipo == EventoSalida.Tipo.EXTRAER_CV
            and legacy.payload.get('job_id') == job.pk):
        return legacy
    # A request UUID identifies this execution, while a content key may have
    # belonged to a deleted job. Never overwrite that older event's history.
    event, _ = EventoSalida.objects.get_or_create(
        clave_idempotencia=f'outbox:cv-job:{job.request_id}',
        defaults={'tipo': EventoSalida.Tipo.EXTRAER_CV, 'payload': {'job_id': job.pk}},
    )
    if event.tipo != EventoSalida.Tipo.EXTRAER_CV or event.payload.get('job_id') != job.pk:
        raise ValueError('El evento de envío no corresponde al trabajo de CV.')
    return event
