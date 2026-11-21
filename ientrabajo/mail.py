"""Branded HTML mail without image attachments or private asset URLs."""
import ipaddress
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils.html import format_html

LOGO_BLOCK = re.compile(r'<!--ien-email-logo-->.*?<!--/ien-email-logo-->', re.S)


def public_url(path):
    base = settings.IEN_PUBLIC_URL.rstrip('/')
    parsed = urlsplit(base)
    return base + path if parsed.scheme in ('http', 'https') and parsed.netloc else ''


def public_logo_url():
    from .templatetags.ien_static import public_static_v
    url = getattr(settings, 'IEN_EMAIL_LOGO_URL', '').strip() or public_static_v('img/ien-trabajo.png')
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or not host or host == 'localhost' or host.endswith(('.localhost', '.local')):
        return ''
    try:
        if not ipaddress.ip_address(host).is_global:
            return ''
    except ValueError:
        pass
    return url


def _logo_image(src):
    return str(format_html('<img src="{}" alt="IEN Trabajo" width="156" height="52" style="display:block;width:156px;height:auto;border:0;">', src))


def send_mail(subject, message, from_email, recipient_list, fail_silently=False,
              auth_user=None, auth_password=None, connection=None, html_message=None):
    connection = connection or get_connection(username=auth_user, password=auth_password, fail_silently=fail_silently)
    email = EmailMultiAlternatives(subject, message, from_email, recipient_list, connection=connection)
    if html_message:
        if LOGO_BLOCK.search(html_message):
            if url := public_logo_url():
                logo = _logo_image(url)
            else:
                logo = '<span style="color:#251a43;font:700 24px Arial,sans-serif;">IEN Trabajo</span>'
            html_message = LOGO_BLOCK.sub(lambda _: logo, html_message)
        email.attach_alternative(html_message, 'text/html')
    return email.send(fail_silently=fail_silently)
