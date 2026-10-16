from django.core import signing
from django.urls import reverse

from .consumers import TOKEN_SALT
from .models import AnalisisCV


def cv_notifications(request):
    user = request.user
    if not user.is_authenticated or not hasattr(user, 'postulante'):
        return {}
    pending = (
        AnalisisCV.objects.filter(postulante=user.postulante, estado=AnalisisCV.Estado.PENDIENTE)
        .values_list('pk', flat=True)
        .first()
    )
    return {
        'cv_notification_token': signing.dumps(user.pk, salt=TOKEN_SALT),
        'cv_pending_analysis_id': pending or '',
        'cv_analysis_status_url': reverse('ia:estado_analisis', args=[0]),
    }
