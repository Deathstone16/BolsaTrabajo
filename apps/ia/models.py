import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from usuarios.models import Postulante


class PrivateCVStorage(FileSystemStorage):
    """Almacén de CV fuera del árbol servido como MEDIA_URL."""

    def __init__(self, location=None, base_url=None, **kwargs):
        super().__init__(
            location=location or Path(settings.BASE_DIR) / 'private_uploads' / 'cv',
            base_url=base_url,
            **kwargs,
        )

    def deconstruct(self):
        return ('ia.models.PrivateCVStorage', (), {})

    def url(self, name):
        raise ValueError('Los CV se entregan únicamente mediante la descarga autorizada.')


private_cv_storage = PrivateCVStorage()


class CVVersion(models.Model):
    """Snapshot inmutable de un CV aceptado del postulante."""

    postulante = models.ForeignKey(Postulante, on_delete=models.CASCADE, related_name='versiones_cv')
    numero = models.PositiveIntegerField()
    archivo = models.FileField(storage=private_cv_storage, upload_to='')
    nombre_original = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64)
    formato = models.CharField(max_length=12)
    tamano = models.PositiveBigIntegerField()
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-numero']
        constraints = [models.UniqueConstraint(fields=['postulante', 'numero'], name='ia_cv_version_numero_unico')]

    def __str__(self):
        return f'CV {self.numero} - {self.postulante}'


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
    version_cv = models.ForeignKey(CVVersion, null=True, blank=True, on_delete=models.SET_NULL, related_name='analisis')
    perfil_snapshot = models.JSONField(null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    respuesta = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    respondido_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-creado_en']
        constraints = []

    def __str__(self):
        return f'Análisis {self.pk} - {self.postulante}'


class EstadoPerfil(models.TextChoices):
    PENDIENTE = 'pending', 'Pending'
    PROCESANDO = 'processing', 'Processing'
    LISTO = 'ready', 'Ready'
    ERROR = 'error', 'Error'
    PROPUESTA = 'proposal_ready', 'Proposal ready'


class PerfilCV(models.Model):
    """Perfil canónico editable; AnalisisCV conserva la respuesta histórica."""

    postulante = models.OneToOneField(Postulante, on_delete=models.CASCADE, related_name='perfil_ia')
    cv_version = models.ForeignKey(CVVersion, null=True, blank=True, on_delete=models.SET_NULL, related_name='perfiles_publicados')
    contenido = models.JSONField(null=True, blank=True)
    version = models.PositiveIntegerField(default=0)
    source_hash = models.CharField(max_length=64, blank=True)
    schema_version = models.CharField(max_length=64, default='candidate-profile.v1')
    estado = models.CharField(max_length=20, choices=EstadoPerfil.choices, default=EstadoPerfil.PENDIENTE)
    origen = models.CharField(max_length=24, default='extraction')
    analisis_fuente = models.ForeignKey(AnalisisCV, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    actualizado_en = models.DateTimeField(auto_now=True)


class VersionPerfilCV(models.Model):
    perfil = models.ForeignKey(PerfilCV, on_delete=models.CASCADE, related_name='versiones')
    version = models.PositiveIntegerField()
    contenido = models.JSONField()
    content_hash = models.CharField(max_length=64)
    origen = models.CharField(max_length=24)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['perfil', 'version'], name='ia_perfil_cv_version_unica')]
        ordering = ['-version']


class PerfilOferta(models.Model):
    oferta = models.OneToOneField('ofertas.Oferta', on_delete=models.CASCADE, related_name='perfil_ia')
    contenido = models.JSONField(null=True, blank=True)
    version = models.PositiveIntegerField(default=0)
    source_hash = models.CharField(max_length=64, blank=True)
    schema_version = models.CharField(max_length=64, default='job-offer.v1')
    estado = models.CharField(max_length=20, choices=EstadoPerfil.choices, default=EstadoPerfil.PENDIENTE)
    actualizado_en = models.DateTimeField(auto_now=True)


class VersionPerfilOferta(models.Model):
    perfil = models.ForeignKey(PerfilOferta, on_delete=models.CASCADE, related_name='versiones')
    version = models.PositiveIntegerField()
    contenido = models.JSONField()
    content_hash = models.CharField(max_length=64)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['perfil', 'version'], name='ia_perfil_oferta_version_unica')]
        ordering = ['-version']


class TrabajoExtraccion(models.Model):
    class Tipo(models.TextChoices):
        CV = 'candidate_cv', 'Candidate CV'
        OFERTA = 'job_offer', 'Job offer'
        NORMALIZAR_PERFIL = 'normalize_profile', 'Normalize candidate profile'

    class Estado(models.TextChoices):
        PENDIENTE = 'pending', 'Pending'
        ENVIANDO = 'sending', 'Sending'
        ACEPTADO = 'accepted', 'Accepted'
        PROCESANDO = 'processing', 'Processing'
        COMPLETADO = 'completed', 'Completed'
        ERROR = 'error', 'Error'
        ENTREGA_INCIERTA = 'delivery_unknown', 'Delivery unknown'

    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    clave_idempotencia = models.CharField(max_length=180, unique=True)
    tipo = models.CharField(max_length=32, choices=Tipo.choices)
    analisis_cv = models.OneToOneField(AnalisisCV, null=True, blank=True, on_delete=models.CASCADE, related_name='trabajo_extraccion')
    oferta = models.ForeignKey('ofertas.Oferta', null=True, blank=True, on_delete=models.CASCADE, related_name='trabajos_extraccion')
    source_hash = models.CharField(max_length=64)
    prompt_version = models.CharField(max_length=64, default='extraction.v1')
    remote_job_id = models.CharField(max_length=64, blank=True)
    cv_snapshot = models.FileField(storage=private_cv_storage, upload_to='snapshots/', null=True, blank=True)
    profile_snapshot = models.JSONField(null=True, blank=True)
    profile_version_base = models.PositiveIntegerField(null=True, blank=True)
    source_cv_version = models.ForeignKey(CVVersion, null=True, blank=True, on_delete=models.SET_NULL, related_name='trabajos_normalizacion')
    estado = models.CharField(max_length=24, choices=Estado.choices, default=Estado.PENDIENTE)
    intentos = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)


class EventoSalida(models.Model):
    class Tipo(models.TextChoices):
        EXTRAER_CV = 'extract_cv', 'Extract CV'
        EXTRAER_OFERTA = 'extract_offer', 'Extract offer'
        NORMALIZAR_PERFIL = 'normalize_profile', 'Normalize profile'
        MATCH = 'match', 'Match'

    class Estado(models.TextChoices):
        PENDIENTE = 'pending', 'Pending'
        ENVIANDO = 'sending', 'Sending'
        ENVIADO = 'sent', 'Sent'
        ERROR = 'error', 'Error'

    tipo = models.CharField(max_length=24, choices=Tipo.choices)
    clave_idempotencia = models.CharField(max_length=180, unique=True)
    payload = models.JSONField(default=dict)
    estado = models.CharField(max_length=16, choices=Estado.choices, default=Estado.PENDIENTE)
    intentos = models.PositiveIntegerField(default=0)
    proximo_intento_en = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)


class EventoRecepcion(models.Model):
    event_id = models.CharField(max_length=100, unique=True)
    recibido_en = models.DateTimeField(auto_now_add=True)

class ComparacionOfertaCV(models.Model):
    """Match solicitado por un postulante usando un análisis de CV guardado."""

    postulante = models.ForeignKey(
        Postulante,
        on_delete=models.CASCADE,
        related_name='comparaciones_ofertas',
    )
    oferta = models.ForeignKey(
        'ofertas.Oferta',
        on_delete=models.CASCADE,
        related_name='comparaciones_cv',
    )
    analisis = models.ForeignKey(
        AnalisisCV,
        on_delete=models.CASCADE,
        related_name='comparaciones_ofertas',
    )
    porcentaje = models.PositiveSmallIntegerField(default=0)
    resultado = models.JSONField(default=dict)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-actualizado_en']
        constraints = [
            models.UniqueConstraint(
                fields=['postulante', 'oferta', 'analisis'],
                name='ia_comparacion_unica_por_oferta_y_analisis',
            ),
        ]

    def __str__(self):
        return f'{self.postulante} - {self.oferta} ({self.porcentaje}%)'
