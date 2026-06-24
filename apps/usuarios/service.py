from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.db import transaction
from .models import Oferente

@transaction.atomic
def aprobar_empresa(oferente_id):
    """
    Aprueba una empresa y la habilita para publicar ofertas.
    @transaction.atomic: si algo falla, se revierte TODO (BD consistente).
    """
    oferente = Oferente.objects.get(id=oferente_id)
    oferente.estado_validacion = 'aprobado'
    oferente.save()
    # Acá después podríamos agregar: enviar_email(oferente)

@transaction.atomic
def rechazar_empresa(oferente_id):
    oferente = Oferente.objects.get(id=oferente_id)
    oferente.estado_validacion = 'rechazado'
    oferente.save()

def puede_publicar_ofertas(oferente):
    """Regla de negocio: solo empresas aprobadas pueden publicar."""
    return oferente.estado_validacion == 'aprobado'

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