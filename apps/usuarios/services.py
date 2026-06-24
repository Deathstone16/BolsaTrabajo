from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings

from .models import Usuario, Postulante, Oferente

token_generator = PasswordResetTokenGenerator()


def get_rol_label(usuario):
    """
    Detecta el rol del usuario según la relación OneToOne existente.
    Compatible con la arquitectura actual (modelos Postulante/Oferente separados).
    """
    try:
        usuario.postulante
        return 'Postulante'
    except Postulante.DoesNotExist:
        pass
    try:
        usuario.oferente
        return 'Oferente'
    except Oferente.DoesNotExist:
        pass
    return 'Usuario'


def enviar_email_recuperacion(usuario, request):
    """
    Genera el token de recuperación y envía el email con el enlace seguro.
    El token expira según PASSWORD_RESET_TIMEOUT (24hs por defecto).
    Retorna True si el usuario existe y el email se intentó enviar.
    """
    uid   = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = token_generator.make_token(usuario)
    link  = request.build_absolute_uri(
        reverse('restablecer-contrasena', args=[uid, token])
    )

    cuerpo = render_to_string('emails/reset_email.txt', {
        'usuario':   usuario,
        'link':      link,
        'rol_label': get_rol_label(usuario),
    })

    cuerpo_html = render_to_string('emails/reset_email.html', {
        'usuario':   usuario,
        'link':      link,
        'rol_label': get_rol_label(usuario),
    })

    send_mail(
        subject='Recuperación de contraseña - IEN Empleo',
        message=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        html_message=cuerpo_html,
        fail_silently=False,
    )


def validar_token_recuperacion(uidb64, token):
    """
    Decodifica el uid y valida el token con PasswordResetTokenGenerator.
    Retorna el Usuario si el token es válido, o None si no lo es.
    """
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    try:
        uid     = force_str(urlsafe_base64_decode(uidb64))
        usuario = Usuario.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        return None

    if not token_generator.check_token(usuario, token):
        return None

    return usuario
