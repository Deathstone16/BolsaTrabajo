from django.db import models

# Create your models here.

class Categoria(models.Model):
    nombre = models.CharField(max_length=120)
class Curso(models.Model):
    nombre = models.CharField(max_length= 120)
    categoria = models.ForeignKey(Categoria,on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='cursos')
    descripcion = models.TextField()
    