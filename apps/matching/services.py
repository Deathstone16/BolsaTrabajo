"""Creación, caché y persistencia de solicitudes de compatibilidad."""

from __future__ import annotations

import json
from copy import deepcopy
import time
from uuid import uuid4
from decimal import Decimal

import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from ien_contracts.models import MatchMetadata, MatchRequest, MatchResult, ScoringConfig
from ien_contracts.utils import content_hash

from ia.models import EventoSalida, EstadoPerfil
from ia.workflow import offer_snapshot

from .configuration import get_active_configuration, scoring_hash, scoring_snapshot
from .models import ResultadoCompatibilidad


def _cache_client():
    return redis.from_url(settings.MATCH_CACHE_REDIS_URL, decode_responses=True)


def _cache_key(cache_key: str) -> str:
    return f"ien:match:result:{cache_key}"


def _save_cache(cache_key: str, result: dict) -> None:
    try:
        _cache_client().set(_cache_key(cache_key), json.dumps(result), ex=settings.MATCH_CACHE_TTL_SECONDS)
    except redis.RedisError:
        pass


def _read_cache(cache_key: str) -> dict | None:
    try:
        value = _cache_client().get(_cache_key(cache_key))
        return json.loads(value) if value else None
    except (redis.RedisError, ValueError):
        return None


def _allow_new_request(postulante_id: int) -> bool:
    """Límite de abuso por usuario; repetir una clave existente no llega aquí."""
    try:
        client = _cache_client()
        key = f"ien:match:user-rate:{postulante_id}"
        now = int(time.time() * 1000)
        cutoff = now - 60 * 60 * 1000
        client.zremrangebyscore(key, 0, cutoff)
        if client.zcard(key) >= settings.MATCH_REQUESTS_PER_HOUR:
            return False
        client.zadd(key, {f'{now}:{uuid4()}': now})
        client.expire(key, 60 * 60)
        return True
    except redis.RedisError:
        # El limitador del proveedor sigue activo en el worker. No se bloquea
        # una consulta propia ya persistida solo por una caída temporal de cache.
        return True


def _notify(match: ResultadoCompatibilidad) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(
            f"match-{match.request_id}",
            {"type": "match.update", "payload": status_payload(match)},
        )
    except (redis.RedisError, OSError):
        # La consulta HTTP recupera el resultado persistido si falla Channels.
        pass


def status_payload(match: ResultadoCompatibilidad) -> dict:
    return {
        "request_id": str(match.request_id),
        "status": match.estado,
        "match_percentage": float(match.match_percentage) if match.match_percentage is not None else None,
        "coverage_percentage": float(match.coverage_percentage) if match.coverage_percentage is not None else None,
        "confidence_percentage": float(match.confidence_percentage) if match.confidence_percentage is not None else None,
        "result": match.resultado if match.estado == ResultadoCompatibilidad.Estado.COMPLETADO else None,
        "error": match.error or None,
        "scoring_config_hash": match.scoring_config_hash,
        "scoring_config": {'version': match.configuracion.version, 'weights': match.scoring_weights} if match.configuracion_id else None,
        "evaluation_date": match.evaluation_date.isoformat() if match.evaluation_date else None,
        "model_version": match.model_version,
        "provider_model_config": match.provider_model_config,
        "confidence_available": bool((match.resultado or {}).get('confidence_available', False)) if match.estado == ResultadoCompatibilidad.Estado.COMPLETADO else False,
    }


@transaction.atomic
def get_or_create_match(postulante, oferta) -> tuple[ResultadoCompatibilidad, bool]:
    # Reload and lock owners before reading profiles. Caller instances may have
    # cached an earlier CV or offer; uploads/callbacks use these same row locks.
    postulante = type(postulante).objects.select_for_update().get(pk=postulante.pk)
    oferta = type(oferta).objects.select_for_update().get(pk=oferta.pk)
    candidate = getattr(postulante, 'perfil_ia', None)
    offer = getattr(oferta, 'perfil_ia', None)
    if candidate is None or candidate.estado != EstadoPerfil.LISTO or not candidate.contenido:
        raise ValueError('Tu perfil todavía no está listo para calcular compatibilidad.')
    if (not postulante.cv_version_actual_id or candidate.cv_version_id != postulante.cv_version_actual_id
            or candidate.schema_version != 'candidate-profile.v2'):
        raise ValueError('El perfil todavía no corresponde a la versión actual del CV.')
    if oferta.requiere_revision_requisitos:
        raise ValueError('La oferta necesita revisar sus requisitos antes de calcular compatibilidad.')
    if offer is None or offer.estado != EstadoPerfil.LISTO or not offer.contenido:
        raise ValueError('La oferta todavía está siendo analizada.')
    if offer.schema_version != 'job-offer.v2':
        raise ValueError('La oferta necesita revisar sus requisitos antes de calcular compatibilidad.')
    from ia.models import TrabajoExtraccion
    input_hash = content_hash(offer_snapshot(oferta))
    latest_offer_job = TrabajoExtraccion.objects.filter(
        tipo=TrabajoExtraccion.Tipo.OFERTA, oferta=oferta,
        estado=TrabajoExtraccion.Estado.COMPLETADO, source_hash=input_hash,
    ).order_by('-actualizado_en').first()
    if not latest_offer_job:
        raise ValueError('La oferta cambió y necesita actualizar su análisis antes de calcular compatibilidad.')
    config = get_active_configuration()
    config_data = scoring_snapshot(config)
    config_digest = scoring_hash(config)
    evaluation_date = timezone.localdate()
    cache_key = content_hash({
        'candidate_id': postulante.pk,
        'offer_id': oferta.pk,
        'candidate_version': candidate.version,
        'offer_version': offer.version,
        'candidate': candidate.source_hash,
        'offer': offer.source_hash,
        'rubric': 'match-rubric.v2',
        'scoring_config_version': config.version,
        'scoring_config_hash': config_digest,
        'evaluation_date': evaluation_date.isoformat(),
        'schema': 'match-result.v2',
        'prompt': 'match-groq.v2',
        'provider_model_config': settings.MATCH_MODEL_VERSION,
        'model': 'provider-managed',
    })
    cached = _read_cache(cache_key)
    match, created = ResultadoCompatibilidad.objects.get_or_create(
        cache_key=cache_key,
        defaults={
            'postulante': postulante,
            'oferta': oferta,
            'perfil_cv_version': candidate.version,
            'perfil_oferta_version': offer.version,
            'perfil_cv_hash': candidate.source_hash,
            'perfil_oferta_hash': offer.source_hash,
            'candidate_snapshot': deepcopy(candidate.contenido),
            'offer_snapshot': deepcopy(offer.contenido),
            'model_version': 'provider-managed',
            'provider_model_config': settings.MATCH_MODEL_VERSION,
            'configuracion': config,
            'scoring_config_hash': config_digest,
            'scoring_weights': config_data['weights'],
            'rubric_version': 'match-rubric.v2',
            'evaluation_date': evaluation_date,
        },
    )
    if cached and match.estado != ResultadoCompatibilidad.Estado.COMPLETADO:
        # El request_id identifica una ejecución, no la versión de los datos.
        # Al rehidratar un cache hit se conserva el resultado de la misma clave
        # pero se asocia al trabajo local recién creado.
        cached = {**cached, 'request_id': str(match.request_id)}
        complete_match(str(match.request_id), cached)
        created = False
    if match.estado == ResultadoCompatibilidad.Estado.COMPLETADO:
        _save_cache(cache_key, match.resultado)
        return match, False
    if match.estado == ResultadoCompatibilidad.Estado.ERROR:
        match.request_id = uuid4()
        match.estado = ResultadoCompatibilidad.Estado.PENDIENTE
        match.error = ''
        match.save(update_fields=['request_id', 'estado', 'error', 'actualizado_en'])
        created = True
    if created:
        if not _allow_new_request(postulante.pk):
            raise ValueError('Alcanzaste el límite de nuevas compatibilidades por hora. Intentá más tarde.')
        EventoSalida.objects.create(
            tipo=EventoSalida.Tipo.MATCH,
            clave_idempotencia=f"outbox:match:{match.request_id}",
            payload={'match_id': match.pk},
        )
    return match, created


def match_request_payload(match: ResultadoCompatibilidad) -> dict:
    if not match.candidate_snapshot or not match.offer_snapshot:
        raise ValueError('Esta solicitud no conserva sus perfiles. Calculá una nueva compatibilidad.')
    if not match.configuracion_id or not match.scoring_weights:
        raise ValueError('Esta compatibilidad no conserva una configuración de pesos. Calculá una nueva.')
    request = MatchRequest(
        protocol_version='match.v2',
        request_id=match.request_id,
        candidate_profile=match.candidate_snapshot,
        job_offer=match.offer_snapshot,
        metadata=MatchMetadata(
            candidate_profile_hash=match.perfil_cv_hash,
            candidate_profile_version=match.perfil_cv_version,
            offer_profile_hash=match.perfil_oferta_hash,
            offer_profile_version=match.perfil_oferta_version,
            rubric_version=match.rubric_version,
            matcher_prompt_version=match.matcher_prompt_version,
            model='provider-managed',
            evaluation_date=match.evaluation_date,
        ),
        scoring_config=ScoringConfig(version=match.configuracion.version, weights=match.scoring_weights),
    )
    return request.model_dump(mode='json')


@transaction.atomic
def complete_match(request_id: str, result: dict) -> ResultadoCompatibilidad:
    validated = MatchResult.model_validate(result).model_dump(mode='json')
    if validated['request_id'] != str(request_id):
        raise ValueError('El resultado no corresponde a esta solicitud.')
    match = ResultadoCompatibilidad.objects.select_for_update().get(request_id=request_id)
    if match.estado in {ResultadoCompatibilidad.Estado.COMPLETADO, ResultadoCompatibilidad.Estado.ERROR}:
        return match
    if validated.get('schema_version') != 'match-result.v2':
        raise ValueError('Se esperaba un resultado match-result.v2.')
    if validated.get('confidence_available') is not False or validated.get('confidence_percentage') is not None:
        raise ValueError('match.v2 no entrega una estimación de confianza cuantificada.')
    expected_scoring = {'version': match.configuracion.version, 'weights': match.scoring_weights}
    if validated.get('scoring_config') != expected_scoring:
        raise ValueError('El resultado usa una configuración de pesos distinta de la solicitada.')
    if not validated.get('breakdown') or not validated.get('mandatory_status'):
        raise ValueError('El resultado v2 debe incluir desglose y estado de requisitos obligatorios.')
    requirements = {item['id']: item for item in match.offer_snapshot.get('requirements', [])}
    seen = set()
    for assessment in validated.get('assessments', []):
        requirement_id = assessment.get('requirement_id')
        expected = requirements.get(requirement_id)
        if expected is None or requirement_id in seen:
            raise ValueError('El resultado contiene requisitos desconocidos o duplicados.')
        seen.add(requirement_id)
        if (assessment.get('category') != expected.get('category')
                or assessment.get('source') != expected.get('source')
                or assessment.get('mandatory') != expected.get('mandatory')):
            raise ValueError('La clasificación del requisito no coincide con la oferta guardada.')
    if seen != set(requirements):
        raise ValueError('El resultado no evaluó todos los requisitos guardados de la oferta.')
    mandatory = [item for item in validated['assessments'] if item['mandatory']]
    if mandatory:
        expected_status = (
            'all_met' if all(item['status'] == 'met' for item in mandatory)
            else 'not_met' if any(item['status'] in {'not_met', 'partial'} for item in mandatory)
            else 'unknown'
        )
        if validated['mandatory_status'] != expected_status:
            raise ValueError('El estado obligatorio no coincide con el detalle de requisitos.')
    match.estado = ResultadoCompatibilidad.Estado.COMPLETADO
    match.resultado = validated
    if validated.get('provider_model'):
        match.model_version = validated['provider_model'][:120]
    match.match_percentage = Decimal(str(validated['match_percentage']))
    match.coverage_percentage = Decimal(str(validated['coverage_percentage']))
    match.confidence_percentage = (
        Decimal(str(validated['confidence_percentage']))
        if validated['confidence_percentage'] is not None else None
    )
    match.error = ''
    match.save()
    _save_cache(match.cache_key, validated)
    transaction.on_commit(lambda: _notify(match))
    return match


@transaction.atomic
def update_match_status(request_id: str, status: str, error: str = '') -> ResultadoCompatibilidad:
    match = ResultadoCompatibilidad.objects.select_for_update().get(request_id=request_id)
    if match.estado in {ResultadoCompatibilidad.Estado.COMPLETADO, ResultadoCompatibilidad.Estado.ERROR}:
        return match
    state = {
        'accepted': ResultadoCompatibilidad.Estado.PENDIENTE,
        'processing': ResultadoCompatibilidad.Estado.PROCESANDO,
        'rate_limited': ResultadoCompatibilidad.Estado.RATE_LIMITED,
        'failed': ResultadoCompatibilidad.Estado.ERROR,
    }.get(status, match.estado)
    order = {
        ResultadoCompatibilidad.Estado.PENDIENTE: 0,
        ResultadoCompatibilidad.Estado.RATE_LIMITED: 1,
        ResultadoCompatibilidad.Estado.PROCESANDO: 2,
    }
    if state in {ResultadoCompatibilidad.Estado.ERROR} or order.get(state, -1) >= order.get(match.estado, -1):
        match.estado = state
    if error:
        match.error = error[:1000]
    match.save()
    transaction.on_commit(lambda: _notify(match))
    return match
