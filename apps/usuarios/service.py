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

from .models import Usuario

token_generator = PasswordResetTokenGenerator()


# --- Autenticación y perfiles ---

def autenticar_usuario(request, email, password):
    user = authenticate(request, email=email, password=password)
    if user is not None:
        auth_login(request, user)
        return True
    return False


def actualizar_datos_postulante(user, form):
    postulante = form.save(commit=False)
    user.first_name = form.cleaned_data['first_name']
    user.last_name = form.cleaned_data['last_name']
    user.email = form.cleaned_data['email']
    user.save()
    postulante.save()


def get_rol_label(usuario):
    if hasattr(usuario, 'postulante'):
        return 'Postulante'
    if hasattr(usuario, 'oferente'):
        return 'Oferente'
    return 'Usuario'


# --- Validación de empresas ---

@transaction.atomic
def aprobar_empresa(oferente):
    """
    Aprueba una empresa y la habilita para publicar ofertas.
    @transaction.atomic: si algo falla, se revierte TODO (BD consistente).
    """
    oferente.estado_validacion = 'aprobado'
    oferente.save()
    # Acá después podríamos agregar: enviar_email(oferente)


@transaction.atomic
def rechazar_empresa(oferente):
    oferente.estado_validacion = 'rechazado'
    oferente.save()


def puede_publicar_ofertas(oferente):
    """Regla de negocio: solo empresas aprobadas pueden publicar."""
    return oferente.estado_validacion == 'aprobado'


def obtener_url_contacto(email_usuario):
    dominio = email_usuario.split('@')[1].lower()
    destino = 'contacto@ien.edu.ar'
    asunto = 'Solicitud de validación de empresa'
    if 'gmail' in dominio:
        return f'https://mail.google.com/mail/?view=cm&fs=1&to={destino}&su={asunto}'
    elif 'outlook' in dominio or 'hotmail' in dominio or 'live' in dominio:
        return f'https://outlook.live.com/mail/0/deeplink/compose?to={destino}&subject={asunto}'
    elif 'yahoo' in dominio:
        return f'https://compose.mail.yahoo.com/?to={destino}&subject={asunto}'
    else:
        return f'mailto:{destino}?subject={asunto}'


# --- Recuperación de contraseña ---

def enviar_email_recuperacion(usuario, request):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = token_generator.make_token(usuario)
    link = request.build_absolute_uri(
        reverse('restablecer-contrasena', args=[uid, token])
    )

    contexto = {
        'usuario': usuario,
        'link': link,
        'rol_label': get_rol_label(usuario),
    }

    send_mail(
        subject='Recuperación de contraseña - IEN Empleo',
        message=render_to_string('emails/reset_email.txt', contexto),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        html_message=render_to_string('emails/reset_email.html', contexto),
        fail_silently=False,
    )


def validar_token_recuperacion(uidb64, token):
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
    """Carga o reemplaza el CV del postulante. Elimina el anterior si existe."""
    if postulante.cv:
        postulante.cv.delete(save=False)
    postulante.cv = archivo
    postulante.cv_fecha_carga = timezone.now()
    postulante.save()


def eliminar_cv(postulante):
    """Elimina el CV del postulante."""
    if postulante.cv:
        postulante.cv.delete(save=False)
        postulante.cv = None
        postulante.cv_fecha_carga = None
        postulante.save()
