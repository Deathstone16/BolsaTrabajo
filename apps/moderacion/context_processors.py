from .models import SolicitudEmpresa
from .notifications import review_notifications


def solicitudes_empresas(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}
    solicitudes = SolicitudEmpresa.objects.select_related('empresa')
    notifications = review_notifications()
    return {
        'solicitudes_empresa_pendientes': solicitudes.filter(resuelta_en__isnull=True, empresa__estado_validacion='pendiente').count(),
        'solicitudes_empresa_recientes': list(solicitudes[:5]),
        'admin_review_notifications': notifications,
    }
