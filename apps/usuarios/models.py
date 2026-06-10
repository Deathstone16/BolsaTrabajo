from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class Usuario(AbstractUser):
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    username = None
    objects = UsuarioManager()
    def __str__(self):
        return self.email

class Postulante(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    dni = models.CharField(max_length=8, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    
    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.email

class Oferente(models.Model):
    
    TAMANO_CHOICES = [
        ('1-10', '1-10 empleados'),
        ('11-50', '11-50 empleados'),
        ('51-200', '51-200 empleados'),
        ('201-1000', '201-1000 empleados'),
        ('1000+', 'Más de 1000 empleados'),
    ]
    
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    nombre_empresa = models.CharField(max_length=200)
    cuit = models.CharField(max_length=13)
    logo = models.ImageField(upload_to='empresas/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='empresas/banners/', null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    industria = models.CharField(max_length=100, null=True, blank=True)
    tamano_empresa = models.CharField(max_length=20, choices=TAMANO_CHOICES, null=True, blank=True)
    ubicacion = models.CharField(max_length=200, null=True, blank=True)
    anio_fundacion = models.IntegerField(null=True, blank=True)
    sitio_web = models.URLField(max_length=300, null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)
    
    def __str__(self):
        return self.nombre_empresa
