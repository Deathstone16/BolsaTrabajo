import uuid

from django.db import models


class ResultadoCompatibilidad(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pending', 'Pending'
        PROCESANDO = 'processing', 'Processing'
        RATE_LIMITED = 'rate_limited', 'Rate limited'
        COMPLETADO = 'completed', 'Completed'
        ERROR = 'error', 'Error'

    postulante = models.ForeignKey('usuarios.Postulante', on_delete=models.CASCADE, related_name='resultados_match')
    oferta = models.ForeignKey('ofertas.Oferta', on_delete=models.CASCADE, related_name='resultados_match')
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    cache_key = models.CharField(max_length=64, unique=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    perfil_cv_version = models.PositiveIntegerField()
    perfil_oferta_version = models.PositiveIntegerField()
    perfil_cv_hash = models.CharField(max_length=64)
    perfil_oferta_hash = models.CharField(max_length=64)
    rubric_version = models.CharField(max_length=64, default='match-rubric.v1')
    matcher_prompt_version = models.CharField(max_length=64, default='match-rubric.v1')
    model_version = models.CharField(max_length=120, default='jev-latest')
    resultado = models.JSONField(null=True, blank=True)
    match_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    coverage_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    confidence_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    error = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['postulante', 'oferta', 'estado'])]
