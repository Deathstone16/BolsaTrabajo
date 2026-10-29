"""
Servicios de autenticación y gestión de usuarios.

Maneja login, registro de postulantes y oferentes,
validación de empresas, recuperación de contraseñas
y carga de CV.
"""

from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from hashlib import sha256
from uuid import uuid4
from django.contrib.auth import logout as auth_logout

from .models import Postulante, Oferente
from .models import Usuario
from ia.models import CVVersion, EstadoPerfil, PerfilCV
from .uploads import normalize_image_upload, validate_cv_upload

token_generator = PasswordResetTokenGenerator()


# --- Autenticación y perfiles ---


def autenticar_usuario(request, email, password):
    """Autentica un usuario con email y password, y lo loguea en la sesión."""
    user = authenticate(request, email=email, password=password)
    if user is not None:
        auth_login(request, user)
        return True
    return False


def actualizar_datos_postulante(user, form):
    """Actualiza los datos del perfil de un postulante desde un formulario."""
    postulante = form.save(commit=False)
    user.first_name = form.cleaned_data["first_name"]
    user.last_name = form.cleaned_data["last_name"]
    user.email = form.cleaned_data["email"]
    user.save()
    postulante.save()


def get_rol_label(usuario):
    """Devuelve el label del rol del usuario: 'Postulante', 'Oferente' o 'Usuario'."""
    if hasattr(usuario, "postulante"):
        return "Postulante"
    if hasattr(usuario, "oferente"):
        return "Oferente"
    return "Usuario"

@transaction.atomic
def registrar_postulante(email, password, first_name, last_name):
    """Registra un nuevo usuario y le crea un perfil de Postulante."""
    user = Usuario.objects.create_user(
        email=email, password=password,
        first_name=first_name, last_name=last_name
    )
    
    Postulante.objects.create(usuario=user)
    return user

@transaction.atomic
def registrar_oferente(email, password, nombre_empresa, cuit):
    """Registra un nuevo usuario y le crea un perfil de Oferente (empresa)."""
    user = Usuario.objects.create_user(email=email, password=password)
    try:
        Oferente.objects.create(
            usuario=user,
            nombre_empresa=nombre_empresa,
            cuit=cuit
        )
    except Exception as a:
        print()
    return user


def cerrar_sesion(request):
    """Cierra la sesión del usuario actual."""
    auth_logout(request)


def es_oferente(user):
    """Verifica si el usuario tiene un perfil de Oferente asociado."""
    return hasattr(user, 'oferente')


def es_postulante(user):
    """Verifica si el usuario tiene un perfil de Postulante asociado."""
    return hasattr(user, 'postulante')



# --- Validación de empresas ---


@transaction.atomic
def aprobar_empresa(oferente):
    """Aprueba una empresa y la habilita para publicar ofertas.

    Args:
        oferente: Instancia del modelo Oferente.
    """
    empresa = Oferente.objects.select_for_update().get(pk=oferente.pk)
    if empresa.estado_validacion == Oferente.EstadoValidacion.APROBADO:
        return False
    empresa.aprobar()
    oferente.estado_validacion = empresa.estado_validacion
    return True


def enviar_email_aprobacion(oferente, dashboard_url):
    """Notifica al oferente después de confirmar la aprobación en la base."""
    contexto = {
        'oferente': oferente,
        'dashboard_url': dashboard_url,
        'contact_email': getattr(settings, 'IEN_CONTACT_EMAIL', ''),
    }
    send_mail(
        subject='Tu empresa fue aprobada - IEN Empleo',
        message=render_to_string('emails/perfil_aprobado.txt', contexto),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[oferente.usuario.email],
        html_message=render_to_string('emails/perfil_aprobado.html', contexto),
        fail_silently=False,
    )


@transaction.atomic
def rechazar_empresa(oferente, motivo=None):
    """Rechaza una empresa y guarda el motivo para que el oferente pueda ver qué corregir.

    Args:
        oferente: Instancia del modelo Oferente.
        motivo (str, optional): Texto explicando el motivo del rechazo.
    """
    oferente.rechazar(motivo=motivo)


@transaction.atomic
def enviar_a_revision(oferente):
    """Resetea el estado de un oferente a pendiente (cuando corrige y reenvía).

    Args:
        oferente: Instancia del modelo Oferente.
    """
    oferente.enviar_a_revision()


def puede_publicar_ofertas(oferente):
    """Verifica si un oferente puede publicar ofertas (solo empresas aprobadas).

    Args:
        oferente: Instancia del modelo Oferente.

    Returns:
        bool: True si el estado es aprobado.
    """
    """Regla de negocio: solo empresas aprobadas pueden publicar."""
    return oferente.estado_obj.puede_publicar()


def obtener_url_contacto(email_usuario=None):
    """Devuelve el contacto institucional configurado, sin depender del correo del usuario."""
    from urllib.parse import urlencode
    email = getattr(settings, 'IEN_CONTACT_EMAIL', '').strip()
    if not email:
        return ''
    return f"mailto:{email}?{urlencode({'subject': 'Solicitud de validación de empresa'})}"


# --- Recuperación de contraseña ---


def enviar_email_recuperacion(usuario, request):
    """Envía email de recuperación de contraseña con token.

    Args:
        usuario: Instancia del modelo Usuario.
        request: HttpRequest para construir la URL absoluta.
    """
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = token_generator.make_token(usuario)
    link = request.build_absolute_uri(
        reverse("restablecer-contrasena", args=[uid, token])
    )

    contexto = {
        "usuario": usuario,
        "link": link,
        "rol_label": get_rol_label(usuario),
    }

    send_mail(
        subject="Recuperación de contraseña - IEN Empleo",
        message=render_to_string("emails/reset_email.txt", contexto),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        html_message=render_to_string("emails/reset_email.html", contexto),
        fail_silently=False,
    )


def validar_token_recuperacion(uidb64, token):
    """Valida el token de recuperación de contraseña.

    Args:
        uidb64 (str): ID del usuario codificado en base64.
        token (str): Token de recuperación.

    Returns:
        Usuario si el token es válido, None si no.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = Usuario.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        return None

    if not token_generator.check_token(usuario, token):
        return None

    return usuario


# --- Gestión de CV ---

@transaction.atomic
def cargar_cv(postulante, archivo):
    """Carga o reemplaza el CV de un postulante.

    Args:
        postulante: Instancia del modelo Postulante.
        archivo: Archivo subido desde el formulario.
    """
    extension, _declared_type, tamano = validate_cv_upload(archivo)
    postulante = Postulante.objects.select_for_update().get(pk=postulante.pk)
    digest = sha256()
    archivo.seek(0)
    for chunk in archivo.chunks():
        digest.update(chunk)
    archivo.seek(0)
    numero = (postulante.versiones_cv.order_by('-numero').values_list('numero', flat=True).first() or 0) + 1
    version = CVVersion(
        postulante=postulante,
        numero=numero,
        nombre_original=archivo.name[:255],
        sha256=digest.hexdigest(),
        formato=extension,
        tamano=tamano,
    )
    version.archivo.save(f'{uuid4().hex}.{extension}', archivo, save=False)
    version.save()
    old_legacy_name = postulante.cv.name if postulante.cv else None
    postulante.cv_version_actual = version
    postulante.cv_fecha_carga = timezone.now()
    postulante.cv = None
    postulante.save(update_fields=['cv_version_actual', 'cv_fecha_carga', 'cv'])
    profile = PerfilCV.objects.select_for_update().filter(postulante=postulante).first()
    if profile:
        profile.estado = EstadoPerfil.PENDIENTE
        profile.save(update_fields=['estado', 'actualizado_en'])
    if old_legacy_name:
        transaction.on_commit(lambda: default_storage.delete(old_legacy_name))
    return version


@transaction.atomic
def eliminar_cv(postulante):
    """Elimina el CV de un postulante y limpia la fecha de carga.

    Args:
        postulante: Instancia del modelo Postulante.
    """
    from ia.models import AnalisisCV
    postulante = Postulante.objects.select_for_update().get(pk=postulante.pk)
    if postulante.cv:
        postulante.cv.delete(save=False)
    postulante.cv = None
    postulante.cv_version_actual = None
    postulante.cv_fecha_carga = None
    postulante.save(update_fields=['cv', 'cv_version_actual', 'cv_fecha_carga'])
    PerfilCV.objects.filter(postulante=postulante).update(estado=EstadoPerfil.PENDIENTE)


def guardar_foto_postulante(postulante, uploaded):
    normalized = normalize_image_upload(uploaded, max_bytes=2 * 1024 * 1024, max_side=1024)
    postulante.foto.save(f'{uuid4().hex}.webp', normalized, save=True)


def guardar_imagen_oferente(oferente, field_name, uploaded):
    limits = {'logo': 2 * 1024 * 1024, 'banner': 5 * 1024 * 1024}
    normalized = normalize_image_upload(uploaded, max_bytes=limits[field_name])
    getattr(oferente, field_name).save(f'{uuid4().hex}.webp', normalized, save=True)
