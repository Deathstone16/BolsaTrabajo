from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    POSTULANTE = 'postulante'
    OFERENTE = 'oferente'
    
    TIPO_CHOICES = [
        (POSTULANTE, 'Postulante'),
        (OFERENTE, 'Oferente'),
    ]

    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', ]
    
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default=POSTULANTE)
    cuit = models.CharField(max_length=13, blank=True, null=True)
    
