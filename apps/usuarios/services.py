from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings

from .models import Usuario, Postulante, Oferente

token_generator = PasswordResetTokenGenerator()


def autenticar_usuario(request, email, password):
    user = authenticate(request, email=email, password=password)
    if user is not None:
        auth_login(request, user)
        return True
    return False


def registrar_usuario(form):
    return form.save()


def actualizar_datos_postulante(user, form):
    postulante = form.save(commit=False)
    user.first_name = form.cleaned_data['first_name']
    user.last_name = form.cleaned_data['last_name']
    user.email = form.cleaned_data['email']
    user.save()
    postulante.save()


def actualizar_perfil_oferente(form):
    form.save()


def get_rol_label(usuario):
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
