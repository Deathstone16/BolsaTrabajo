"""Creación, caché y persistencia de solicitudes de compatibilidad."""

from __future__ import annotations

import json
import time
from uuid import uuid4
from decimal import Decimal

import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import IntegrityError, transaction

from ien_contracts.models import MatchMetadata, MatchRequest, MatchResult
from ien_contracts.utils import content_hash

from ia.models import EventoSalida, EstadoPerfil

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
    async_to_sync(layer.group_send)(
        f"match-{match.request_id}",
        {"type": "match.update", "payload": status_payload(match)},
    )


def status_payload(match: ResultadoCompatibilidad) -> dict:
    return {
        "request_id": str(match.request_id),
        "status": match.estado,
        "match_percentage": float(match.match_percentage) if match.match_percentage is not None else None,
        "coverage_percentage": float(match.coverage_percentage) if match.coverage_percentage is not None else None,
        "confidence_percentage": float(match.confidence_percentage) if match.confidence_percentage is not None else None,
        "result": match.resultado if match.estado == ResultadoCompatibilidad.Estado.COMPLETADO else None,
        "error": match.error or None,
    }


@transaction.atomic
def get_or_create_match(postulante, oferta) -> tuple[ResultadoCompatibilidad, bool]:
    candidate = postulante.perfil_ia
    offer = oferta.perfil_ia
    if candidate.estado != EstadoPerfil.LISTO or not candidate.contenido:
        raise ValueError('Tu perfil todavía no está listo para calcular compatibilidad.')
    if offer.estado != EstadoPerfil.LISTO or not offer.contenido:
        raise ValueError('La oferta todavía está siendo analizada.')
    cache_key = content_hash({
        'candidate': candidate.source_hash,
        'offer': offer.source_hash,
        'rubric': 'match-rubric.v1',
        'schema': 'match-result.v1',
        'model': 'jev-latest',
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
    candidate = match.postulante.perfil_ia
    offer = match.oferta.perfil_ia
    request = MatchRequest(
        request_id=match.request_id,
        candidate_profile=candidate.contenido,
        job_offer=offer.contenido,
        metadata=MatchMetadata(
            candidate_profile_hash=match.perfil_cv_hash,
            candidate_profile_version=match.perfil_cv_version,
            offer_profile_hash=match.perfil_oferta_hash,
            offer_profile_version=match.perfil_oferta_version,
            rubric_version=match.rubric_version,
            matcher_prompt_version=match.matcher_prompt_version,
            model=match.model_version,
        ),
    )
    return request.model_dump(mode='json')


@transaction.atomic
def complete_match(request_id: str, result: dict) -> ResultadoCompatibilidad:
    validated = MatchResult.model_validate(result).model_dump(mode='json')
    match = ResultadoCompatibilidad.objects.select_for_update().get(request_id=request_id)
    if match.estado == ResultadoCompatibilidad.Estado.COMPLETADO:
        return match
    match.estado = ResultadoCompatibilidad.Estado.COMPLETADO
    match.resultado = validated
    match.match_percentage = Decimal(str(validated['match_percentage']))
    match.coverage_percentage = Decimal(str(validated['coverage_percentage']))
    match.confidence_percentage = Decimal(str(validated['confidence_percentage']))
    match.error = ''
    match.save()
    _save_cache(match.cache_key, validated)
    transaction.on_commit(lambda: _notify(match))
    return match


@transaction.atomic
def update_match_status(request_id: str, status: str, error: str = '') -> ResultadoCompatibilidad:
    match = ResultadoCompatibilidad.objects.select_for_update().get(request_id=request_id)
    state = {
        'accepted': ResultadoCompatibilidad.Estado.PENDIENTE,
        'processing': ResultadoCompatibilidad.Estado.PROCESANDO,
        'rate_limited': ResultadoCompatibilidad.Estado.RATE_LIMITED,
        'failed': ResultadoCompatibilidad.Estado.ERROR,
    }.get(status, match.estado)
    match.estado = state
    if error:
        match.error = error[:1000]
    match.save()
    transaction.on_commit(lambda: _notify(match))
    return match
