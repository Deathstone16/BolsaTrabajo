from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    POSTULANTE = 'postulante'
    OFERENTE = 'oferente'
    
    TIPO_CHOICES = [
        (POSTULANTE, 'Postulante'),
        (OFERENTE, 'Oferente'),
    ]
    
    nombre_completo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default=POSTULANTE)
    cuit = models.CharField(max_length=13, blank=True, null=True)
    
    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name='usuarios_usuario'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='usuarios_usuario'
    )