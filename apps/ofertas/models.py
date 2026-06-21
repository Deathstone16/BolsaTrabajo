from django.db import models
from django.conf import settings
from django.utils import timezone

class CategoriaOferta(models.Model):

    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Categoría de Oferta"
        verbose_name_plural = "Categorías de Ofertas"

    def __str__(self):
        return self.nombre

class Oferta(models.Model):
    
    MODALIDAD_CHOICES = [
        ('presencial', 'Presencial'),
        ('remoto', 'Remoto'),
        ('hibrido', 'Híbrido'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Aprobación'),
        ('activa', 'Activa'),
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

    
    empresa = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ofertas')
    categoria = models.ForeignKey('CategoriaOferta', on_delete=models.SET_NULL, null=True, blank=True, related_name='ofertas')
    titulo = models.CharField(max_length=100)
    nombre_puesto = models.CharField(max_length=150)
    ubicacion = models.CharField(max_length=100)
    modalidad = models.CharField(max_length=20, choices=MODALIDAD_CHOICES, default='presencial')
    descripcion = models.TextField()
    requisitos = models.TextField()
    habilidades_requeridas = models.TextField()
    experiencia_requerida = models.CharField(max_length=100) # Ej: "2-3 años"
    nivel_educativo = models.CharField(max_length=30, choices=NIVEL_EDUCATIVO_CHOICES)
    es_confidencial = models.BooleanField(default=False)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_publicacion = models.DateTimeField(default=timezone.now)
    fecha_cierre = models.DateTimeField()
    
    class Meta:
        verbose_name = "Oferta"
        verbose_name_plural = "Ofertas"
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return f"{self.titulo} - {self.nombre_puesto}"  