from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import SolicitudEmpresa


@receiver(post_save, sender='usuarios.Oferente', dispatch_uid='solicitud_revision_empresa')
def registrar_solicitud_empresa(sender, instance, raw=False, **kwargs):
    if raw:
        return
    if instance.estado_validacion == 'pendiente':
        SolicitudEmpresa.objects.get_or_create(empresa=instance, resuelta_en__isnull=True)
    else:
        SolicitudEmpresa.objects.filter(empresa=instance, resuelta_en__isnull=True).update(
            estado=instance.estado_validacion, resuelta_en=timezone.now(),
        )
