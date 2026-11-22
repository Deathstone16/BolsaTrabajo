"""Historial persistente de solicitudes de aprobación y recordatorios."""
from django.db import models
from django.utils import timezone


def vencimiento_recordatorio():
    # Se conserva el nombre para las migraciones existentes, sin demora de envío.
    return timezone.now()


class SolicitudEmpresa(models.Model):
    empresa = models.ForeignKey('usuarios.Oferente', on_delete=models.CASCADE, related_name='solicitudes_revision')
    creada_en = models.DateTimeField(default=timezone.now)
    recordar_desde = models.DateTimeField(default=vencimiento_recordatorio, db_index=True)
    estado = models.CharField(max_length=12, choices=[('pendiente', 'Pendiente'), ('aprobado', 'Aprobada'), ('rechazado', 'Rechazada')], default='pendiente')
    resuelta_en = models.DateTimeField(null=True, blank=True)
    recordatorio_enviado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-creada_en', '-pk']
        constraints = [models.UniqueConstraint(fields=['empresa'], condition=models.Q(resuelta_en__isnull=True), name='una_solicitud_empresa_pendiente')]


class ControlRecordatorios(models.Model):
    """Reserva de envío entre procesos y espera breve para reintentos SMTP."""
    clave = models.CharField(max_length=40, primary_key=True, default='empresas')
    reservado_hasta = models.DateTimeField(null=True, blank=True)
    token = models.UUIDField(null=True, blank=True)
    proximo_envio_en = models.DateTimeField(null=True, blank=True)
    ultimo_envio_en = models.DateTimeField(null=True, blank=True)
