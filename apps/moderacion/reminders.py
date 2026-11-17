"""Un resumen diferido, sin enviar correo en el registro ni en las visitas web."""
import logging
from datetime import timedelta
from uuid import uuid4
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from usuarios.models import Usuario
from .models import ControlRecordatorios, SolicitudEmpresa

logger = logging.getLogger(__name__)


def destinatarios_recordatorio():
    emails = settings.IEN_REVIEW_EMAILS or list(Usuario.objects.filter(
        is_staff=True, is_active=True,
    ).exclude(email='').values_list('email', flat=True))
    result = []
    for email in emails:
        validate_email(email)
        if email.lower() not in {item.lower() for item in result}:
            result.append(email)
    return result


def enviar_recordatorios_empresas():
    now = timezone.now()
    # Una actualización condicional reclama el lease incluso con SQLite.
    ControlRecordatorios.objects.get_or_create(clave='empresas')
    token = uuid4()
    claimed = ControlRecordatorios.objects.filter(clave='empresas').filter(
        Q(reservado_hasta__isnull=True) | Q(reservado_hasta__lte=now),
    ).filter(Q(proximo_envio_en__isnull=True) | Q(proximo_envio_en__lte=now)).update(
        reservado_hasta=now + timedelta(minutes=5), token=token,
    )
    if not claimed:
        return 0
    try:
        solicitudes = list(SolicitudEmpresa.objects.select_related('empresa').filter(
            resuelta_en__isnull=True, empresa__estado_validacion='pendiente',
            recordatorio_enviado_en__isnull=True, recordar_desde__lte=now,
        ).order_by('creada_en'))
        if not solicitudes:
            return 0
        recipients = destinatarios_recordatorio()
        public_url = settings.IEN_PUBLIC_URL
        parsed = urlsplit(public_url)
        if not recipients or parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise ValidationError('Configurá IEN_REVIEW_EMAILS (o administradores activos) e IEN_PUBLIC_URL para los recordatorios.')
        # Volver a comprobar antes de preparar el resumen: no recordar resoluciones recientes.
        ids = [solicitud.pk for solicitud in solicitudes]
        solicitudes = list(SolicitudEmpresa.objects.select_related('empresa').filter(
            pk__in=ids, resuelta_en__isnull=True, empresa__estado_validacion='pendiente',
        ).order_by('creada_en'))
        if not solicitudes:
            return 0
        context = {
            'solicitudes': solicitudes, 'cantidad': len(solicitudes),
            'review_url': public_url + reverse('mod_solicitudes_empresas') + '?estado=pendiente',
            'horas': settings.IEN_COMPANY_REMINDER_HOURS,
        }
        sent = send_mail(
            subject=f'IEN Empleo: {len(solicitudes)} empresa(s) pendiente(s) de revisión',
            message=render_to_string('emails/empresas_pendientes.txt', context),
            html_message=render_to_string('emails/empresas_pendientes.html', context),
            from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=recipients,
            fail_silently=False,
        )
        if sent != 1:
            raise RuntimeError('El proveedor no aceptó el correo de recordatorio.')
        sent_at = timezone.now()
        SolicitudEmpresa.objects.filter(pk__in=[item.pk for item in solicitudes]).update(recordatorio_enviado_en=sent_at)
        ControlRecordatorios.objects.filter(clave='empresas', token=token).update(
            ultimo_envio_en=sent_at,
            proximo_envio_en=sent_at + timedelta(hours=settings.IEN_COMPANY_REMINDER_HOURS),
        )
        return len(solicitudes)
    except Exception:
        # Conservar las solicitudes para reintentar luego, sin perderlas ni bloquear el alta.
        ControlRecordatorios.objects.filter(clave='empresas', token=token).update(
            proximo_envio_en=timezone.now() + timedelta(hours=1),
        )
        logger.exception('No se pudo enviar el resumen de solicitudes de empresas.')
        return 0
    finally:
        ControlRecordatorios.objects.filter(clave='empresas', token=token).update(reservado_hasta=None, token=None)
