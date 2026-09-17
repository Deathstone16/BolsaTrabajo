from django.db import models
from usuarios.models import Postulante


class AnalisisCV(models.Model):
    """Solicitud de análisis y respuesta recibida desde el servicio externo."""

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        COMPLETADO = 'completado', 'Completado'
        ERROR = 'error', 'Error'

    postulante = models.ForeignKey(
        Postulante,
        on_delete=models.CASCADE,
        related_name='analisis_cv',
    )
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    respuesta = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    respondido_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-creado_en']

    def __str__(self):
        return f'Análisis {self.pk} - {self.postulante}'
