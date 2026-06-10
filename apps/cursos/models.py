from django.db import models

# Create your models here.

class Categoria(models.Model):
    nombre = models.CharField(max_length=120)
    def __str__(self):
        return self.nombre

class Curso(models.Model):
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
    