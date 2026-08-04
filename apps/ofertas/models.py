from django.db import models
from django.conf import settings
from django.utils import timezone
from .state import ESTADOS
from categorias.models import Categoria, TipoOferta





class Oferta(models.Model):
    
    MODALIDAD_CHOICES = [
        ('presencial', 'Presencial'),
        ('remoto', 'Remoto'),
        ('hibrido', 'Híbrido'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Aprobación'),
        ('activa', 'Activa'),
        ('rechazada', 'Rechazada'),
        ('finalizada', 'Finalizada'),
        
    ]

    EXPERIENCIA_CHOICES = [
        ('sin-experiencia', 'Sin experiencia'),
        ('menos-1', 'Menos de 1 año'),
        ('1-2', '1-2 años'),
        ('2-3', '2-3 años'),
        ('3-5', '3-5 años'),
        ('5+', '5+ años'),
    ]

    NIVEL_EDUCATIVO_CHOICES = [
        ('secundario', 'Secundario Completo / Bachillerato'),
        ('terciario', 'Terciario'),
        ('universitario', 'Universitario'),
        ('posgrado', 'Posgrado / Master'),
    ]

    
    empresa = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    tipo_oferta = models.ForeignKey(TipoOferta, null=True, blank=True, on_delete=models.SET_NULL)
    titulo = models.CharField(max_length=100)
    nombre_puesto = models.CharField(max_length=150)
    ubicacion = models.CharField(max_length=100)
    modalidad = models.CharField(max_length=20, choices=MODALIDAD_CHOICES, default='presencial')
    descripcion = models.TextField()
    habilidades_requeridas = models.TextField()
    experiencia_requerida = models.CharField(max_length=20, choices=EXPERIENCIA_CHOICES, default='sin-experiencia')
    nivel_educativo = models.CharField(max_length=30, choices=NIVEL_EDUCATIVO_CHOICES)
    es_confidencial = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_publicacion = models.DateTimeField(default=timezone.now)
    fecha_cierre = models.DateTimeField()
    motivo_rechazo = models.TextField(null=True, blank=True)
    
    
    class Meta:
        verbose_name = "Oferta"
        verbose_name_plural = "Ofertas"
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return f"{self.titulo} - {self.nombre_puesto}"  
    
    def get_state(self):
        
        return ESTADOS[self.estado]

    def aprobar(self):
        self.get_state().aprobar(self)

    def rechazar(self):
        self.get_state().rechazar(self)

    def finalizar(self):
        self.get_state().finalizar(self)

    def puede_editarse(self):
        return self.get_state().puede_editarse()