import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.db import models


def nueva_version_configuracion():
    return f'config-{uuid.uuid4().hex[:12]}'


class ConfiguracionCompatibilidad(models.Model):
    """Rúbrica inmutable al publicarse; los borradores siguen siendo editables."""

    version = models.CharField('Versión', max_length=64, unique=True, default=nueva_version_configuracion)
    technical_skills = models.DecimalField('Competencias técnicas (%)', max_digits=5, decimal_places=2, default=Decimal('35.00'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    soft_skills = models.DecimalField('Habilidades blandas (%)', max_digits=5, decimal_places=2, default=Decimal('15.00'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    experience = models.DecimalField('Experiencia (%)', max_digits=5, decimal_places=2, default=Decimal('20.00'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    education = models.DecimalField('Educación (%)', max_digits=5, decimal_places=2, default=Decimal('10.00'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    languages = models.DecimalField('Idiomas (%)', max_digits=5, decimal_places=2, default=Decimal('5.00'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    logistics = models.DecimalField('Logística y modalidad (%)', max_digits=5, decimal_places=2, default=Decimal('5.00'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    desirables = models.DecimalField('Requisitos deseables (%)', max_digits=5, decimal_places=2, default=Decimal('10.00'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    es_borrador = models.BooleanField('Es borrador', default=True)
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Creada por', null=True, blank=True, on_delete=models.SET_NULL, related_name='configuraciones_compatibilidad_creadas')
    publicada_por = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Publicada por', null=True, blank=True, on_delete=models.SET_NULL, related_name='configuraciones_compatibilidad_publicadas')
    creada_en = models.DateTimeField('Creada el', auto_now_add=True)
    publicada_en = models.DateTimeField('Publicada el', null=True, blank=True)

    FIELDS = ('technical_skills', 'soft_skills', 'experience', 'education', 'languages', 'logistics', 'desirables')

    class Meta:
        verbose_name = 'Configuración de compatibilidad'
        verbose_name_plural = 'Configuraciones de compatibilidad'
        permissions = [('publicar_configuracioncompatibilidad', 'Puede publicar configuraciones de compatibilidad')]

    def clean(self):
        super().clean()
        weights = [getattr(self, field) for field in self.FIELDS]
        if any(value is None or not value.is_finite() or value < Decimal('0') or value > Decimal('100') for value in weights):
            raise ValidationError('Cada peso debe estar entre 0 y 100%.')
        total = sum(weights, Decimal('0'))
        if total > Decimal('100'):
            raise ValidationError({'__all__': f'La suma de los porcentajes es {total}%. No puede superar 100%.'})
        if not self.es_borrador and total != Decimal('100'):
            raise ValidationError({'__all__': f'La suma es {total}%. La configuración publicada debe sumar exactamente 100%.'})

    def save(self, *args, **kwargs):
        if self.pk and not getattr(self, '_publishing', False):
            old = type(self).objects.filter(pk=self.pk).values_list('es_borrador', flat=True).first()
            if old is False:
                raise ValidationError('Una configuración publicada es inmutable. Creá un borrador para editar los pesos.')
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not self.es_borrador:
            raise ValidationError('Una configuración publicada no se puede eliminar.')
        return super().delete(*args, **kwargs)

    def pesos_basis_points(self):
        return {field: int(getattr(self, field) * 100) for field in self.FIELDS}

    def __str__(self):
        return f'{self.version} (borrador)' if self.es_borrador else self.version


class ConfiguracionActiva(models.Model):
    """Puntero bloqueable para serializar publicaciones concurrentes."""

    configuracion = models.ForeignKey(ConfiguracionCompatibilidad, on_delete=models.PROTECT)
    singleton = models.CharField(max_length=16, unique=True, default='actual')


class ResultadoCompatibilidad(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pending', 'Pending'
        PROCESANDO = 'processing', 'Processing'
        RATE_LIMITED = 'rate_limited', 'Rate limited'
        COMPLETADO = 'completed', 'Completed'
        ERROR = 'error', 'Error'
        CANCELADO = 'cancelled', 'Cancelado'

    postulante = models.ForeignKey('usuarios.Postulante', on_delete=models.CASCADE, related_name='resultados_match')
    oferta = models.ForeignKey('ofertas.Oferta', on_delete=models.CASCADE, related_name='resultados_match')
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    cache_key = models.CharField(max_length=64, unique=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    perfil_cv_version = models.PositiveIntegerField()
    perfil_oferta_version = models.PositiveIntegerField()
    perfil_cv_hash = models.CharField(max_length=64)
    perfil_oferta_hash = models.CharField(max_length=64)
    rubric_version = models.CharField(max_length=64, default='match-rubric.v2')
    matcher_prompt_version = models.CharField(max_length=64, default='match-groq.v2')
    model_version = models.CharField(max_length=120, default='provider-managed')
    provider_model_config = models.CharField(max_length=120, default='')
    configuracion = models.ForeignKey(ConfiguracionCompatibilidad, null=True, blank=True, on_delete=models.PROTECT, related_name='resultados')
    scoring_config_hash = models.CharField(max_length=64, default='')
    scoring_weights = models.JSONField(default=dict)
    evaluation_date = models.DateField(null=True, blank=True)
    resultado = models.JSONField(null=True, blank=True)
    candidate_snapshot = models.JSONField(default=dict)
    offer_snapshot = models.JSONField(default=dict)
    match_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    coverage_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    confidence_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    error = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['postulante', 'oferta', 'estado'])]
