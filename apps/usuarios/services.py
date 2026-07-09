from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import logout as auth_logout
from .models import Postulante, Oferente
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

@transaction.atomic
def registrar_postulante(email, password, first_name, last_name):
    user = Usuario.objects.create_user(
        email=email, password=password,
        first_name=first_name, last_name=last_name
    )
    
    Postulante.objects.create(usuario=user)
    return user

@transaction.atomic
def registrar_oferente(email, password, nombre_empresa, cuit):
    user = Usuario.objects.create_user(email=email, password=password)
    Oferente.objects.create(
        usuario=user,
        nombre_empresa=nombre_empresa,
        cuit=cuit
    )
    return user


def cerrar_sesion(request):
    auth_logout(request)


def es_oferente(user):
    return hasattr(user, 'oferente')


def es_postulante(user):
    return hasattr(user, 'postulante')



# --- Validación de empresas ---

@transaction.atomic
def aprobar_empresa(oferente):
    oferente.aprobar()
    
  
@transaction.atomic
def rechazar_empresa(oferente):
    oferente.rechazar()
    


def puede_publicar_ofertas(oferente):
    return oferente.esta_aprobado


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




