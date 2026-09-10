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
from django.contrib.auth import logout as auth_logout

from .models import Postulante, Oferente
from .models import Usuario

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
    oferente.aprobar()


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


def obtener_url_contacto(email_usuario):
    """Genera URL de contacto según el dominio del email (Gmail, Outlook, etc.).

    Args:
        email_usuario (str): Email del usuario.

    Returns:
        str: URL del cliente de correo con destinatario prellenado.
    """
    dominio = email_usuario.split("@")[1].lower()
    destino = "contacto@ien.edu.ar"
    asunto = "Solicitud de validación de empresa"
    if "gmail" in dominio:
        return f"https://mail.google.com/mail/?view=cm&fs=1&to={destino}&su={asunto}"
    elif "outlook" in dominio or "hotmail" in dominio or "live" in dominio:
        return f"https://outlook.live.com/mail/0/deeplink/compose?to={destino}&subject={asunto}"
    elif "yahoo" in dominio:
        return f"https://compose.mail.yahoo.com/?to={destino}&subject={asunto}"
    else:
        return f"mailto:{destino}?subject={asunto}"


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

def cargar_cv(postulante, archivo):
    """Carga o reemplaza el CV de un postulante.

    Args:
        postulante: Instancia del modelo Postulante.
        archivo: Archivo subido desde el formulario.
    """
    if postulante.cv:
        postulante.cv.delete(save=False)
    postulante.cv = archivo
    postulante.cv_fecha_carga = timezone.now()
    postulante.save()


def eliminar_cv(postulante):
    """Elimina el CV de un postulante y limpia la fecha de carga.

    Args:
        postulante: Instancia del modelo Postulante.
    """
    if postulante.cv:
        postulante.cv.delete(save=False)
        postulante.cv = None
        postulante.cv_fecha_carga = None
        postulante.save()
