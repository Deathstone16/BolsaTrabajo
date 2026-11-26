"""Recognize retries of one registration without storing passwords or logging in."""
import logging
from hashlib import sha256
from uuid import uuid4
from django.core import signing
from django.core.cache import cache
from .models import Usuario

SALT = 'ien-registration-attempt.v1'
TTL = 900
logger = logging.getLogger(__name__)


def _key(token, role):
    if not isinstance(token, str) or len(token) > 1024:
        return None
    try:
        data = signing.loads(token, salt=SALT, max_age=TTL)
    except (signing.BadSignature, ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get('role') != role:
        return None
    return 'ien:registration:' + sha256(token.encode()).hexdigest()


def form_token(request, role):
    previous = request.POST.get('registration_attempt', '') if request.method == 'POST' else ''
    return previous if _key(previous, role) else signing.dumps({'nonce': uuid4().hex, 'role': role}, salt=SALT)


def completed_retry(request, role):
    key = _key(request.POST.get('registration_attempt', ''), role)
    if not key:
        return False
    try:
        user_id = cache.get(key)
    except Exception:
        logger.warning('Registration retry cache unavailable')
        return False
    if user_id is None:
        return False
    user = Usuario.objects.filter(pk=user_id).first()
    password = request.POST.get('password1', '')
    return bool(user and user.email.casefold() == request.POST.get('email', '').strip().casefold()
                and password == request.POST.get('password2') and user.check_password(password))


def remember_success(request, role, user):
    key = _key(request.POST.get('registration_attempt', ''), role)
    if key:
        try:
            cache.set(key, user.pk, timeout=TTL)
        except Exception:
            logger.warning('Registration retry cache unavailable')
