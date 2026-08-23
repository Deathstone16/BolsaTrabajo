"""
Modelos de cursos y categorías.

Define ``Curso`` con sus tipos (Presencial, Virtual, Híbrido)
y su relación con ``Categoria``.
"""

from django.db import models
from categorias.models import Categoria

# Create your models here.



class Curso(models.Model):
    """Modelo de curso del instituto con tipo, duración y horario."""
    PRESENCIAL = 'Presencial'
    VIRTUAL = 'Virtual'
    HIBRIDO = 'Hibrido'
    
    TIPO_CHOICES= [
        (PRESENCIAL , 'Presencial'),
        (VIRTUAL , 'Virtual'),
        (HIBRIDO , 'Hibrido'),
    ]


    nombre = models.CharField(max_length= 120)
    categoria = models.ForeignKey(Categoria,on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='cursos')
    descripcion = models.TextField()
    duracion = models.CharField(max_length=100)
    horario = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20,choices=TIPO_CHOICES,default=PRESENCIAL)
    url_externa=models.URLField(blank=True,null=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
    