"""Conserva el aviso de rechazo; la aprobación se envía desde sus vistas."""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="usuarios.Oferente")
def notificar_cambio_estado_perfil(sender, instance, created, **kwargs):
    """Dispara email cuando el estado_validacion de un oferente cambia."""

    # Si es la creación inicial, no enviar email
    if created:
        # Inicializar el estado actual en la primera guarda
        if not hasattr(instance, '_previous_estado_validacion'):
            from django.apps import apps
            Oferente = apps.get_model('usuarios', 'Oferente')
            campo_estado = Oferente._meta.get_field('estado_validacion')
            instance._previous_estado_validacion = campo_estado.default
        return

    # Obtener el valor actual y anterior del estado
    valor_actual = instance.estado_validacion
    valor_anterior = getattr(instance, '_previous_estado_validacion', None)

    # Primera vez que se guarda, solo guardamos el estado actual
    if valor_anterior is None:
        instance._previous_estado_validacion = valor_actual
        return

    # La aprobación se notifica desde moderación o admin, después de guardar.
    if valor_anterior == 'pendiente' and valor_actual == 'rechazado':
        from .services import notificar_perfil_rechazado
        motivo = getattr(instance, 'motivo_rechazo', 'No especificado')
        notificar_perfil_rechazado(instance, motivo)

    # Actualizar el estado anterior para la próxima guarda
    instance._previous_estado_validacion = valor_actual
