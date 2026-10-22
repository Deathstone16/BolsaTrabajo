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
    CVVersion,
    EstadoPerfil,
    EventoRecepcion,
    EventoSalida,
    PerfilCV,
    PerfilOferta,
    TrabajoExtraccion,
    VersionPerfilCV,
    VersionPerfilOferta,
)

CV_PROMPT_VERSION = 'cv-extraction.v2-packets-soft.v6'
OFFER_PROMPT_VERSION = 'offer-extraction.v2'
PROFILE_NORMALIZATION_PROMPT_VERSION = 'profile-normalization.v2'


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

    requirements = oferta.requisitos_estructurados or []
    if oferta.requiere_revision_requisitos:
        raise ValueError('La clasificación de requisitos de esta oferta necesita revisión antes del análisis.')
    return {
        "schema_version": "job-offer.v2",
        "offer_id": str(oferta.pk),
        "title": oferta.titulo,
        "location": oferta.ubicacion,
        "work_mode": {'presencial': 'onsite', 'remoto': 'remote', 'hibrido': 'hybrid'}.get(oferta.modalidad, 'unknown'),
        "summary": oferta.descripcion[:2500],
        "minimum_experience_months": None,
        "education_levels": [],
        "languages": [],
        "requirements": requirements,
    }


@transaction.atomic
def request_cv_extraction(postulante) -> tuple[AnalisisCV, TrabajoExtraccion, bool]:
    postulante = type(postulante).objects.select_for_update().get(pk=postulante.pk)
    version = postulante.cv_version_actual
    if version is None:
        raise ValueError('Primero cargá una versión válida de tu CV.')
    source_hash = version.sha256
    analysis = AnalisisCV.objects.filter(
        version_cv=version,
        estado=AnalisisCV.Estado.COMPLETADO,
        trabajo_extraccion__prompt_version=CV_PROMPT_VERSION,
    ).first()
    if analysis:
        key = analysis.trabajo_extraccion.clave_idempotencia
    else:
        analysis = AnalisisCV.objects.filter(
            version_cv=version,
            estado=AnalisisCV.Estado.PENDIENTE,
            trabajo_extraccion__prompt_version=CV_PROMPT_VERSION,
        ).first()
        created_analysis = analysis is None
        if analysis is None:
            analysis = AnalisisCV.objects.create(postulante=postulante, version_cv=version)
        key = f"candidate-cv:{version.pk}:{source_hash}:{CV_PROMPT_VERSION}"
        existing_for_analysis = TrabajoExtraccion.objects.filter(analisis_cv=analysis).first()
        if existing_for_analysis:
            key = existing_for_analysis.clave_idempotencia
        else:
            prior = TrabajoExtraccion.objects.filter(clave_idempotencia=key).first()
            if prior and prior.estado == TrabajoExtraccion.Estado.ERROR and (created_analysis or analysis):
                # La nueva intención y su análisis se crean bajo el lock del postulante;
                # los POST siguientes recuperan el job por analisis_cv arriba.
                key = f'{key}:retry:{uuid4().hex[:8]}'
    job, job_created = TrabajoExtraccion.objects.get_or_create(
        clave_idempotencia=key,
        defaults={
            "tipo": TrabajoExtraccion.Tipo.CV,
            "analisis_cv": analysis,
            "source_hash": source_hash,
            "prompt_version": CV_PROMPT_VERSION,
            "profile_version_base": PerfilCV.objects.filter(postulante=postulante).values_list('version', flat=True).first() or 0,
        },
    )
    if job_created:
        with version.archivo.open('rb') as cv_file:
            job.cv_snapshot.save(f'{version.sha256}.{version.formato}', File(cv_file), save=True)
    EventoSalida.objects.get_or_create(
        clave_idempotencia=f"outbox:{key}",
        defaults={
            "tipo": EventoSalida.Tipo.EXTRAER_CV,
            "payload": {"job_id": job.pk},
        },
    )
    profile, _ = PerfilCV.objects.get_or_create(postulante=postulante, defaults={"estado": EstadoPerfil.PENDIENTE})
    if analysis.estado != AnalisisCV.Estado.COMPLETADO and profile.estado != EstadoPerfil.PROCESANDO:
        profile.estado = EstadoPerfil.PENDIENTE
        profile.save(update_fields=['estado', 'actualizado_en'])
    return analysis, job, job_created


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
            "profile_snapshot": snapshot,
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
    postulante = type(postulante).objects.select_for_update().get(pk=postulante.pk)
    profile = PerfilCV.objects.select_for_update().get(postulante=postulante)
    if profile.version != profile_version_base:
        raise ValueError('The profile version changed before the edit could be normalized.')
    if not postulante.cv_version_actual_id or profile.cv_version_id != postulante.cv_version_actual_id:
        raise ValueError('El CV cambió. Esperá a que termine el análisis de la versión vigente.')

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
            'source_cv_version': postulante.cv_version_actual,
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
def publish_candidate_profile(postulante, content: dict[str, Any], source_hash: str, origin: str, analysis: AnalisisCV | None = None, cv_version: CVVersion | None = None) -> PerfilCV:
    content = {**content, 'schema_version': 'candidate-profile.v2'}
    validated = CandidateProfile.model_validate(content).model_dump(mode='json')
    if validated['profile_id'] != str(postulante.pk):
        raise ValueError('El perfil no corresponde al postulante de este trabajo.')
    profile, _ = PerfilCV.objects.select_for_update().get_or_create(postulante=postulante)
    cv_version = cv_version or (analysis.version_cv if analysis and analysis.version_cv_id else postulante.cv_version_actual)
    new_hash = content_hash(validated)
    if profile.contenido and profile.source_hash == new_hash:
        profile.estado = EstadoPerfil.LISTO
        profile.cv_version = cv_version
        profile.analisis_fuente = analysis or profile.analisis_fuente
        profile.save(update_fields=['estado', 'cv_version', 'analisis_fuente', 'actualizado_en'])
        return profile
    profile.version += 1
    profile.contenido = validated
    profile.source_hash = new_hash
    profile.schema_version = validated['schema_version']
    profile.estado = EstadoPerfil.LISTO
    profile.origen = origin
    profile.analisis_fuente = analysis
    profile.cv_version = cv_version
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
    if validated['schema_version'] != 'job-offer.v2' or validated['offer_id'] != str(oferta.pk):
        raise ValueError('El perfil no corresponde a la oferta de este trabajo o usa un esquema anterior.')
    profile, _ = PerfilOferta.objects.select_for_update().get_or_create(oferta=oferta)
    profile_hash = content_hash(validated)
    if profile.contenido and profile.source_hash == profile_hash:
        profile.estado = EstadoPerfil.LISTO
        profile.save(update_fields=['estado', 'actualizado_en'])
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
        with transaction.atomic():
            EventoRecepcion.objects.create(event_id=event_id)
    except IntegrityError:
        return False
    # Nullable select_related joins cannot all be locked by PostgreSQL. Lock
    # only the job here; related owners are locked explicitly below in order.
    job = TrabajoExtraccion.objects.select_for_update(of=('self',)).filter(
        clave_idempotencia=payload['request_id'], source_hash=payload['source_hash']
    ).select_related('analisis_cv__postulante', 'oferta').first()
    if job is None:
        raise TrabajoExtraccion.DoesNotExist(payload['request_id'])
    if job.remote_job_id and payload.get('job_id') and job.remote_job_id != payload['job_id']:
        raise ValueError('Callback job ID does not match the accepted extraction job.')
    if job.tipo == TrabajoExtraccion.Tipo.CV:
        analysis = job.analisis_cv
        if (not analysis or payload.get('kind') != 'candidate_cv'
                or type(payload.get('candidate_id')) is not int
                or type(payload.get('analysis_id')) is not int
                or (payload.get('cv_version_id') is not None and type(payload.get('cv_version_id')) is not int)
                or payload.get('candidate_id') != analysis.postulante_id
                or payload.get('analysis_id') != analysis.pk
                or (payload.get('cv_version_id') is not None and payload.get('cv_version_id') != analysis.version_cv_id)
                or payload.get('offer_id') is not None
                or analysis.version_cv_id is None
                or analysis.version_cv.sha256 != job.source_hash):
            raise ValueError('Callback owner, analysis, or CV version does not match the extraction job.')
    elif job.tipo == TrabajoExtraccion.Tipo.OFERTA:
        if (not job.oferta or payload.get('kind') != 'job_offer'
                or payload.get('offer_id') != job.oferta_id
                or payload.get('candidate_id') is not None
                or payload.get('analysis_id') is not None):
            raise ValueError('Callback offer does not match the extraction job.')
    elif job.tipo == TrabajoExtraccion.Tipo.NORMALIZAR_PERFIL:
        owner_id = job.source_cv_version.postulante_id if job.source_cv_version_id else None
        if (payload.get('kind') != 'profile_normalization'
                or not owner_id or payload.get('candidate_id') != owner_id
                or payload.get('analysis_id') is not None
                or payload.get('offer_id') is not None):
            raise ValueError('Callback owner or CV version does not match the normalization job.')
    if job.estado in {TrabajoExtraccion.Estado.COMPLETADO, TrabajoExtraccion.Estado.ERROR}:
        return False
    # Todas las mutaciones del perfil siguen el mismo orden que la carga de CV:
    # Postulante primero y PerfilCV después. Esto evita validar contra una FK
    # cacheada mientras una carga nueva ya dejó atrás a este job.
    locked_postulante = None
    locked_profile = None
    if job.tipo == TrabajoExtraccion.Tipo.CV and job.analisis_cv_id:
        from usuarios.models import Postulante
        locked_postulante = Postulante.objects.select_for_update().get(pk=job.analisis_cv.postulante_id)
        analysis = AnalisisCV.objects.select_for_update().get(pk=job.analisis_cv_id)
        job.analisis_cv = analysis
        locked_profile = PerfilCV.objects.select_for_update().filter(postulante_id=locked_postulante.pk).first()
        if payload['status'] == 'completed' and locked_profile is None:
            locked_profile = PerfilCV.objects.create(postulante=locked_postulante)
    elif job.tipo == TrabajoExtraccion.Tipo.NORMALIZAR_PERFIL and job.source_cv_version_id:
        from usuarios.models import Postulante
        locked_postulante = Postulante.objects.select_for_update().get(pk=job.source_cv_version.postulante_id)
        locked_profile = PerfilCV.objects.select_for_update().filter(postulante_id=locked_postulante.pk).first()
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
            current = locked_postulante and locked_postulante.cv_version_actual_id == job.analisis_cv.version_cv_id
            if current and locked_profile and locked_profile.version == job.profile_version_base:
                locked_profile.estado = EstadoPerfil.ERROR
                locked_profile.save(update_fields=['estado', 'actualizado_en'])
        elif job.tipo == TrabajoExtraccion.Tipo.NORMALIZAR_PERFIL:
            if (locked_profile and locked_postulante
                    and locked_profile.version == job.profile_version_base
                    and locked_postulante.cv_version_actual_id == job.source_cv_version_id
                    and locked_profile.cv_version_id == job.source_cv_version_id):
                locked_profile.estado = EstadoPerfil.ERROR
                locked_profile.save(update_fields=['estado', 'actualizado_en'])
        return True

    result = payload['result']
    if job.tipo == TrabajoExtraccion.Tipo.CV:
        analysis = job.analisis_cv
        if (not analysis or payload.get('candidate_id') != analysis.postulante_id
                or not analysis.version_cv_id or analysis.version_cv.sha256 != job.source_hash):
            raise ValueError('Candidate does not match the extraction job.')
        validated_profile = CandidateProfile.model_validate(result)
        if (validated_profile.schema_version != 'candidate-profile.v2'
                or validated_profile.profile_id != str(analysis.postulante_id)):
            raise ValueError('Candidate profile owner or schema does not match the extraction job.')
        analysis.respuesta = payload
        analysis.perfil_snapshot = validated_profile.model_dump(mode='json')
        analysis.estado = AnalisisCV.Estado.COMPLETADO
        analysis.error = ''
        analysis.respondido_en = timezone.now()
        analysis.save(update_fields=['respuesta', 'perfil_snapshot', 'estado', 'error', 'respondido_en'])
        if (locked_postulante and locked_profile
                and locked_postulante.cv_version_actual_id == analysis.version_cv_id
                and locked_profile.version == job.profile_version_base):
            publish_candidate_profile(locked_postulante, result, job.source_hash, 'extraction', analysis, analysis.version_cv)
    elif job.tipo == TrabajoExtraccion.Tipo.OFERTA:
        if not job.oferta or payload.get('offer_id') != job.oferta_id:
            raise ValueError('Offer does not match the extraction job.')
        current_offer = type(job.oferta).objects.select_for_update().get(pk=job.oferta_id)
        if not current_offer.requiere_revision_requisitos:
            current_snapshot_hash = content_hash(offer_snapshot(current_offer))
            if current_snapshot_hash == job.source_hash:
                publish_offer_profile(current_offer, result, job.source_hash)
    elif job.tipo == TrabajoExtraccion.Tipo.NORMALIZAR_PERFIL:
        candidate_id = payload.get('candidate_id')
        if not candidate_id:
            raise ValueError('Candidate is required for profile normalization.')
        profile = locked_profile
        if (not profile or not locked_postulante or profile.version != job.profile_version_base
                or not job.source_cv_version_id
                or locked_postulante.cv_version_actual_id != job.source_cv_version_id
                or profile.cv_version_id != job.source_cv_version_id):
            raise ValueError('Profile changed while the normalization was in progress.')
        publish_candidate_profile(locked_postulante, result, job.source_hash, 'user_edit', cv_version=job.source_cv_version)
    job.estado = TrabajoExtraccion.Estado.COMPLETADO
    job.error = ''
    job.save(update_fields=['remote_job_id', 'estado', 'error', 'actualizado_en'])
    return True
