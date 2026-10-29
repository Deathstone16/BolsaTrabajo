"""Correo transaccional por HTTPS para los planes que bloquean SMTP."""

import base64
from email.utils import parseaddr
from smtplib import SMTPException

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


def _address(value):
    name, email = parseaddr(value)
    return {'email': email, **({'name': name} if name else {})}


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            try:
                if not settings.BREVO_API_KEY:
                    raise SMTPException('Falta configurar BREVO_API_KEY.')
                message.message()  # Conserva la validación de encabezados de Django.
                payload = {'sender': _address(message.from_email), 'subject': message.subject}
                for field in ('to', 'cc', 'bcc'):
                    if recipients := getattr(message, field):
                        payload[field] = [_address(item) for item in recipients]
                if message.reply_to:
                    payload['replyTo'] = _address(message.reply_to[0])
                payload['htmlContent' if message.content_subtype == 'html' else 'textContent'] = message.body
                for content, mimetype in getattr(message, 'alternatives', ()):
                    if mimetype == 'text/html':
                        payload['htmlContent'] = content
                if message.attachments:
                    payload['attachment'] = []
                    for filename, content, _ in message.attachments:
                        if isinstance(content, str):
                            content = content.encode('utf-8')
                        payload['attachment'].append({'name': filename, 'content': base64.b64encode(content).decode('ascii')})
                response = requests.post(
                    'https://api.brevo.com/v3/smtp/email', json=payload,
                    headers={'api-key': settings.BREVO_API_KEY, 'accept': 'application/json'},
                    timeout=settings.EMAIL_TIMEOUT,
                )
                if response.status_code != 201:
                    raise SMTPException(f'El proveedor de correo rechazó el envío (HTTP {response.status_code}).')
                sent += 1
            except (requests.RequestException, SMTPException, ValueError, TypeError):
                if not self.fail_silently:
                    raise SMTPException('No se pudo enviar el correo; revisá la configuración del proveedor HTTPS.') from None
        return sent
