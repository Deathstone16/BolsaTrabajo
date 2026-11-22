from django.db.models.signals import post_save
from django.db import transaction
from django.dispatch import receiver
from django.utils import timezone
from .models import SolicitudEmpresa
from .reminders import enviar_recordatorios_empresas


@receiver(post_save, sender='usuarios.Oferente', dispatch_uid='solicitud_revision_empresa')
def registrar_solicitud_empresa(sender, instance, raw=False, **kwargs):
    if raw:
        return
    if instance.estado_validacion == 'pendiente':
        solicitud, creada = SolicitudEmpresa.objects.get_or_create(empresa=instance, resuelta_en__isnull=True)
        if creada:
            # No avisar sobre un alta que luego se revierta. Guardar el perfil de
            # nuevo no genera otra solicitud ni otro correo.
            transaction.on_commit(
                lambda pk=solicitud.pk: enviar_recordatorios_empresas(solicitud_id=pk),
                robust=True,
            )
    else:
        SolicitudEmpresa.objects.filter(empresa=instance, resuelta_en__isnull=True).update(
            estado=instance.estado_validacion, resuelta_en=timezone.now(),
        )
