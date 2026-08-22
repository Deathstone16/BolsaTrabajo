from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from .estado_oferente import ESTADOS, Pendiente


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
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
    cv = models.FileField(upload_to='postulantes/cv/', blank=True, null=True)
    cv_fecha_carga = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.email


class OferenteManager(models.Manager):
    def pendientes(self):
        """Empresas que aún no fueron validadas."""
        return self.filter(estado_validacion=self.model.EstadoValidacion.PENDIENTE)

    def aprobados(self):
        """Empresas que pueden publicar ofertas."""
        return self.filter(estado_validacion=self.model.EstadoValidacion.APROBADO)


class Oferente(models.Model):
    objects = OferenteManager()

    class EstadoValidacion(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de Validación'
        APROBADO = 'aprobado', 'Aprobada'
        RECHAZADO = 'rechazado', 'Rechazada'

    TAMANO_CHOICES = [
        ("1-10", "1-10 empleados"),
        ("11-50", "11-50 empleados"),
        ("51-200", "51-200 empleados"),
        ("201-1000", "201-1000 empleados"),
        ("1000+", "Más de 1000 empleados"),
    ]

    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    estado_validacion = models.CharField(
        max_length=20,
        choices=EstadoValidacion.choices,
        default=EstadoValidacion.PENDIENTE,
    )
    motivo_rechazo = models.TextField(blank=True, null=True)
    nombre_empresa = models.CharField(max_length=200)
    cuit = models.CharField(max_length=13)
    logo = models.ImageField(upload_to="empresas/logos/", null=True, blank=True)
    banner = models.ImageField(upload_to="empresas/banners/", null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    industria = models.CharField(max_length=100, null=True, blank=True)
    tamano_empresa = models.CharField(
        max_length=20, choices=TAMANO_CHOICES, null=True, blank=True
    )
    ubicacion = models.CharField(max_length=200, null=True, blank=True)
    anio_fundacion = models.IntegerField(null=True, blank=True)
    sitio_web = models.URLField(max_length=300, null=True, blank=True)
    telefono = models.CharField(max_length=50, null=True, blank=True)

    def aprobar(self):
        self.estado_validacion = self.EstadoValidacion.APROBADO
        self.save(update_fields=['estado_validacion'])

    def rechazar(self, motivo=None):
        self.estado_validacion = self.EstadoValidacion.RECHAZADO
        self.motivo_rechazo = motivo
        self.save(update_fields=['estado_validacion', 'motivo_rechazo'])

    def enviar_a_revision(self):
        self.estado_validacion = self.EstadoValidacion.PENDIENTE
        self.motivo_rechazo = None
        self.save(update_fields=['estado_validacion', 'motivo_rechazo'])

    @property
    def estado_obj(self):
        """Devuelve el objeto de estado según el valor en BD."""
        return ESTADOS.get(self.estado_validacion, Pendiente())

    def __str__(self):
        return self.nombre_empresa