"""Operaciones transaccionales de extracción y perfiles canónicos."""

from __future__ import annotations

from hashlib import sha256
from typing import Any
from uuid import uuid4

from django.core.files import File
from django.db import IntegrityError, transaction
from django.utils import timezone

from ien_contracts.models import CandidateProfile, JobOffer
from ien_contracts.utils import content_hash

from .models import (
    AnalisisCV,
    EstadoPerfil,
    EventoRecepcion,
    EventoSalida,
    PerfilCV,
    PerfilOferta,
    TrabajoExtraccion,
    VersionPerfilCV,
    VersionPerfilOferta,
)

CV_PROMPT_VERSION = 'cv-extraction.v1'
OFFER_PROMPT_VERSION = 'offer-extraction.v1'
PROFILE_NORMALIZATION_PROMPT_VERSION = 'profile-normalization.v1'


def _cv_source_hash(postulante) -> str:
    with postulante.cv.open('rb') as cv_file:
        digest = sha256()
        for block in iter(lambda: cv_file.read(1024 * 128), b''):
            digest.update(block)
    return digest.hexdigest()


def offer_snapshot(oferta) -> dict[str, Any]:
    """Snapshot estable con los únicos campos que afectan la extracción."""

    def skills(value: str) -> list[str]:
        return sorted({item.strip() for item in (value or '').split(',') if item.strip()}, key=str.casefold)

    return {
        "title": oferta.titulo,
        "role": oferta.nombre_puesto,
        "location": oferta.ubicacion,
        "work_mode": oferta.modalidad,
        "description": oferta.descripcion,
        "hard_skills": skills(oferta.habilidades_duras or oferta.habilidades_requeridas),
        "soft_skills": skills(oferta.habilidades_blandas),
        "experience_requirement": oferta.experiencia_requerida,
        "education_requirement": oferta.nivel_educativo,
    }


@transaction.atomic
def request_cv_extraction(postulante) -> tuple[AnalisisCV, TrabajoExtraccion, bool]:
    source_hash = _cv_source_hash(postulante)
    analysis, created = AnalisisCV.objects.get_or_create(
        postulante=postulante,
        estado=AnalisisCV.Estado.PENDIENTE,
    )
    key = f"candidate-cv:{analysis.pk}:{source_hash}:{CV_PROMPT_VERSION}"
    job, job_created = TrabajoExtraccion.objects.get_or_create(
        clave_idempotencia=key,
        defaults={
            "tipo": TrabajoExtraccion.Tipo.CV,
            "analisis_cv": analysis,
            "source_hash": source_hash,
            "prompt_version": CV_PROMPT_VERSION,
        },
    )
    if job_created:
        with postulante.cv.open('rb') as cv_file:
            job.cv_snapshot.save(
                postulante.cv.name.rsplit('/', 1)[-1],
                File(cv_file),
                save=True,
            )
    EventoSalida.objects.get_or_create(
        clave_idempotencia=f"outbox:{key}",
        defaults={
            "tipo": EventoSalida.Tipo.EXTRAER_CV,
            "payload": {"job_id": job.pk},
        },
    )
    profile, profile_created = PerfilCV.objects.get_or_create(postulante=postulante, defaults={"estado": EstadoPerfil.PENDIENTE})
    if job_created and not profile_created:
        profile.estado = EstadoPerfil.PENDIENTE
        profile.save(update_fields=['estado', 'actualizado_en'])
    return analysis, job, created or job_created


@transaction.atomic
def request_offer_extraction(oferta) -> tuple[TrabajoExtraccion, bool]:
    snapshot = offer_snapshot(oferta)
    source_hash = content_hash(snapshot)
    key = f"job-offer:{oferta.pk}:{source_hash}:{OFFER_PROMPT_VERSION}"
    job, created = TrabajoExtraccion.objects.get_or_create(
        clave_idempotencia=key,
        defaults={
            "tipo": TrabajoExtraccion.Tipo.OFERTA,
            "oferta": oferta,
            "source_hash": source_hash,
            "prompt_version": OFFER_PROMPT_VERSION,
        },
    )
    EventoSalida.objects.get_or_create(
        clave_idempotencia=f"outbox:{key}",
        defaults={"tipo": EventoSalida.Tipo.EXTRAER_OFERTA, "payload": {"job_id": job.pk}},
    )
    profile, profile_created = PerfilOferta.objects.get_or_create(
        oferta=oferta,
        defaults={"estado": EstadoPerfil.PENDIENTE, "source_hash": source_hash},
    )
    if created and not profile_created:
        profile.estado = EstadoPerfil.PENDIENTE
        profile.save(update_fields=['estado', 'actualizado_en'])
    return job, created


@transaction.atomic
def request_profile_normalization(postulante, content: dict[str, Any], profile_version_base: int) -> tuple[TrabajoExtraccion, bool]:
    """Normaliza una edición antes de que pueda alimentar los cálculos de match."""

    normalized_input = CandidateProfile.model_validate(content).model_dump(mode='json')
    profile = PerfilCV.objects.select_for_update().get(postulante=postulante)
    if profile.version != profile_version_base:
        raise ValueError('The profile version changed before the edit could be normalized.')

    source_hash = content_hash(normalized_input)
    base_key = f"candidate-profile:{postulante.pk}:v{profile_version_base}:{source_hash}:{PROFILE_NORMALIZATION_PROMPT_VERSION}"
    previous = TrabajoExtraccion.objects.filter(clave_idempotencia=base_key).first()
    key = base_key if previous is None or previous.estado != TrabajoExtraccion.Estado.ERROR else f"{base_key}:retry:{uuid4().hex[:8]}"
    job, created = TrabajoExtraccion.objects.get_or_create(
        clave_idempotencia=key,
        defaults={
            'tipo': TrabajoExtraccion.Tipo.NORMALIZAR_PERFIL,
            'source_hash': source_hash,
            'prompt_version': PROFILE_NORMALIZATION_PROMPT_VERSION,
            'profile_snapshot': normalized_input,
            'profile_version_base': profile_version_base,
        },
    )
    if created:
        EventoSalida.objects.create(
            clave_idempotencia=f"outbox:{key}",
            tipo=EventoSalida.Tipo.NORMALIZAR_PERFIL,
            payload={'job_id': job.pk},
        )
    profile.estado = EstadoPerfil.PROCESANDO
    profile.save(update_fields=['estado', 'actualizado_en'])
    return job, created


@transaction.atomic
def publish_candidate_profile(postulante, content: dict[str, Any], source_hash: str, origin: str, analysis: AnalisisCV | None = None) -> PerfilCV:
    validated = CandidateProfile.model_validate(content).model_dump(mode='json')
    profile, _ = PerfilCV.objects.select_for_update().get_or_create(postulante=postulante)
    new_hash = content_hash(validated)
    if profile.contenido and profile.source_hash == new_hash:
        return profile
    profile.version += 1
    profile.contenido = validated
    profile.source_hash = new_hash
    profile.schema_version = validated['schema_version']
    profile.estado = EstadoPerfil.LISTO
    profile.origen = origin
    profile.analisis_fuente = analysis
    profile.save()
    VersionPerfilCV.objects.create(
        perfil=profile,
        version=profile.version,
        contenido=validated,
        content_hash=new_hash,
        origen=origin,
    )
    return profile


@transaction.atomic
def publish_offer_profile(oferta, content: dict[str, Any], source_hash: str) -> PerfilOferta:
    validated = JobOffer.model_validate(content).model_dump(mode='json')
    profile, _ = PerfilOferta.objects.select_for_update().get_or_create(oferta=oferta)
    profile_hash = content_hash(validated)
    if profile.contenido and profile.source_hash == profile_hash:
        return profile
    profile.version += 1
    profile.contenido = validated
    profile.source_hash = profile_hash
    profile.schema_version = validated['schema_version']
    profile.estado = EstadoPerfil.LISTO
    profile.save()
    VersionPerfilOferta.objects.create(
        perfil=profile,
        version=profile.version,
        contenido=validated,
        content_hash=profile_hash,
    )
    return profile


@transaction.atomic
def receive_extraction_event(payload: dict[str, Any]) -> bool:
    """Aplica un callback una vez y evita que un resultado viejo pise el vigente."""

    event_id = payload['event_id']
    try:
        EventoRecepcion.objects.create(event_id=event_id)
    except IntegrityError:
        return False
    job = TrabajoExtraccion.objects.select_for_update().filter(
        clave_idempotencia=payload['request_id'], source_hash=payload['source_hash']
    ).select_related('analisis_cv__postulante', 'oferta').first()
    if job is None:
        raise TrabajoExtraccion.DoesNotExist(payload['request_id'])
    job.remote_job_id = payload.get('job_id') or job.remote_job_id
    if payload['status'] != 'completed':
        job.estado = TrabajoExtraccion.Estado.ERROR
        job.error = payload.get('error') or 'Extraction service failed.'
        job.save(update_fields=['remote_job_id', 'estado', 'error', 'actualizado_en'])
        if job.analisis_cv:
            job.analisis_cv.estado = AnalisisCV.Estado.ERROR
            job.analisis_cv.error = job.error
            job.analisis_cv.respondido_en = timezone.now()
            job.analisis_cv.save(update_fields=['estado', 'error', 'respondido_en'])
        elif job.tipo == TrabajoExtraccion.Tipo.NORMALIZAR_PERFIL:
            profile = PerfilCV.objects.select_for_update().filter(postulante_id=payload.get('candidate_id')).first()
            if profile:
                profile.estado = EstadoPerfil.ERROR
                profile.save(update_fields=['estado', 'actualizado_en'])
        return True

    result = payload['result']
    if job.tipo == TrabajoExtraccion.Tipo.CV:
        analysis = job.analisis_cv
        if not analysis or payload.get('candidate_id') != analysis.postulante_id:
            raise ValueError('Candidate does not match the extraction job.')
        analysis.respuesta = payload
        analysis.estado = AnalisisCV.Estado.COMPLETADO
        analysis.error = ''
        analysis.respondido_en = timezone.now()
        analysis.save(update_fields=['respuesta', 'estado', 'error', 'respondido_en'])
        profile = PerfilCV.objects.select_for_update().get(postulante=analysis.postulante)
        latest_cv_job = TrabajoExtraccion.objects.filter(
            tipo=TrabajoExtraccion.Tipo.CV,
            analisis_cv__postulante_id=analysis.postulante_id,
        ).order_by('-creado_en').first()
        if latest_cv_job and latest_cv_job.pk == job.pk:
            publish_candidate_profile(analysis.postulante, result, job.source_hash, 'extraction', analysis)
    elif job.tipo == TrabajoExtraccion.Tipo.OFERTA:
        if not job.oferta or payload.get('offer_id') != job.oferta_id:
            raise ValueError('Offer does not match the extraction job.')
        if content_hash(offer_snapshot(job.oferta)) == job.source_hash:
            publish_offer_profile(job.oferta, result, job.source_hash)
    elif job.tipo == TrabajoExtraccion.Tipo.NORMALIZAR_PERFIL:
        candidate_id = payload.get('candidate_id')
        if not candidate_id:
            raise ValueError('Candidate is required for profile normalization.')
        profile = PerfilCV.objects.select_for_update().filter(postulante_id=candidate_id).first()
        if not profile or profile.version != job.profile_version_base:
            raise ValueError('Profile changed while the normalization was in progress.')
        publish_candidate_profile(profile.postulante, result, job.source_hash, 'user_edit')
    job.estado = TrabajoExtraccion.Estado.COMPLETADO
    job.error = ''
    job.save(update_fields=['remote_job_id', 'estado', 'error', 'actualizado_en'])
    return True
