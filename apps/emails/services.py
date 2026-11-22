"""
Servicios de notificación por email para ofertas laborales.

Contiene funciones que teñen y envían emails cuando ocurren
eventos importantes en el ciclo de vida de una oferta.
"""

from ientrabajo.mail import send_mail, public_url
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse


def notificar_oferta_aprobada(oferta, offerente):
    """
    Envía email de notificación cuando una oferta es aprobada.

    Args:
        oferta: Instancia del modelo Oferta que fue aprobada.
        offerente: Instancia del modelo Oferente (usuario empresa).
    """
    # 1. Preparar el contexto que las plantillas van a usar
    context = {
        "offerente": offerente,
        "oferta": oferta,
        "offer_url": public_url(reverse("detalle_oferta", args=[oferta.pk])),
        "year": 2026,
    }

    # 2. Enviar el email usando la configuración ya existente en settings
    send_mail(
        subject="Tu oferta fue aprobada - IEN Trabajo",
        # Versión texto plano (se usa si el HTML no carga)
        message=render_to_string("emails/oferta_aprobada.txt", context),
        # Remitente desde settings DEFAULT_FROM_EMAIL
        from_email=settings.DEFAULT_FROM_EMAIL,
        # A quién va dirigido (email del offerente)
        recipient_list=[offerente.usuario.email if hasattr(offerente, "usuario") else offerente.email],
        # Versión HTML (bonito con estilos y links)
        html_message=render_to_string("emails/oferta_aprobada.html", context),
        # Si es False, los errores se silencian (no recomendado en producción)
        fail_silently=False,
    )


def notificar_oferta_rechazada(oferta, offerente, motivo_rechazo=None):
    """
    Envía email de notificación cuando una oferta es rechazada.

    Args:
        oferta: Instancia del modelo Oferta que fue rechazada.
        offerente: Instancia del modelo Oferente (usuario empresa).
        motivo_rechazo: Texto explicando por qué se rechazó (puede ser None).
    """
    # 1. Preparar el contexto (agregamos el motivo en este caso)
    context = {
        "offerente": offerente,
        "oferta": oferta,
        "motivo_rechazo": motivo_rechazo or "No especificado",
        "offer_url": public_url(reverse("editar_oferta", args=[oferta.pk])),
        "year": 2026,
    }

    # 2. Enviar el email
    send_mail(
        subject="Revisión de tu oferta - IEN Trabajo",
        message=render_to_string("emails/oferta_rechazada.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[offerente.usuario.email if hasattr(offerente, "usuario") else offerente.email],
        html_message=render_to_string("emails/oferta_rechazada.html", context),
        fail_silently=False,
    )


def notificar_perfil_rechazado(oferente, motivo_rechazo=None):
    """
    Envía email de notificación cuando el perfil de la empresa es rechazado.

    Args:
        oferente: Instancia del modelo Oferente (usuario empresa).
        motivo_rechazo: Texto explicando el motivo del rechazo.
    """
    context = {
        "oferente": oferente,
        "motivo_rechazo": motivo_rechazo or "No especificado",
        "edit_url": public_url(reverse("editar_perfil_empresa")),
        "year": 2026,
    }

    send_mail(
        subject="Revisión de tu empresa - IEN Trabajo",
        message=render_to_string("emails/perfil_rechazado.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[oferente.usuario.email],
        html_message=render_to_string("emails/perfil_rechazado.html", context),
        fail_silently=False,
    )
