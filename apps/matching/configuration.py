"""Publicación y serialización de la rúbrica de compatibilidad."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from ien_contracts.utils import content_hash

from .models import ConfiguracionActiva, ConfiguracionCompatibilidad


def scoring_snapshot(config):
    weights = config.pesos_basis_points()
    return {
        'version': str(config.version),
        'weights': weights,
    }


def scoring_hash(config):
    return content_hash(scoring_snapshot(config))


def get_active_configuration():
    active = ConfiguracionActiva.objects.select_related('configuracion').filter(singleton='actual').first()
    if not active or active.configuracion.es_borrador:
        raise ValueError('No hay una configuración válida de compatibilidad publicada.')
    return active.configuracion


@transaction.atomic
def publish_configuration(config_id, user):
    if not (user.is_superuser or user.has_perm('matching.publicar_configuracioncompatibilidad')):
        raise PermissionDenied('No tenés permiso para publicar configuraciones de compatibilidad.')
    active = ConfiguracionActiva.objects.select_for_update().filter(singleton='actual').first()
    config = ConfiguracionCompatibilidad.objects.select_for_update().get(pk=config_id)
    if not config.es_borrador:
        if active and active.configuracion_id == config.pk:
            return config
        raise ValidationError('La configuración ya fue publicada y no se puede volver a editar.')
    config.es_borrador = False
    config.publicada_por = user
    config.publicada_en = timezone.now()
    config._publishing = True
    config.full_clean()
    config.save(update_fields=['es_borrador', 'publicada_por', 'publicada_en'])
    if active:
        active.configuracion = config
        active.save(update_fields=['configuracion'])
    else:
        ConfiguracionActiva.objects.create(singleton='actual', configuracion=config)
    return config
