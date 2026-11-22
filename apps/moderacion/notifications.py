"""Read-only review notifications for the institute administrator."""
from django.urls import reverse

from ofertas.models import Oferta
from .models import SolicitudEmpresa


def review_notifications():
    companies = SolicitudEmpresa.objects.select_related('empresa')
    offers = Oferta.objects.select_related('empresa__oferente').order_by('-fecha_publicacion', '-pk')
    company_count = companies.filter(resuelta_en__isnull=True, empresa__estado_validacion='pendiente').count()
    offer_count = offers.filter(estado='pendiente').count()
    # Pending reviews must not be pushed out of the bell by newer resolved items.
    company_items = list(companies.filter(resuelta_en__isnull=True, empresa__estado_validacion='pendiente')[:5])
    company_items += list(companies.exclude(pk__in=[item.pk for item in company_items])[:5])
    offer_items = list(offers.filter(estado='pendiente')[:5])
    offer_items += list(offers.exclude(pk__in=[item.pk for item in offer_items])[:5])
    items = [{
        'titulo': item.empresa.nombre_empresa, 'tipo': 'Empresa',
        'estado': item.get_estado_display(), 'fecha': item.creada_en.isoformat(),
        'url': reverse('mod_detalle_empresa', args=[item.empresa_id]),
        'pending': item.resuelta_en is None and item.empresa.estado_validacion == 'pendiente',
    } for item in company_items]
    items += [{
        'titulo': item.titulo, 'tipo': 'Oferta',
        'estado': item.get_estado_display(), 'fecha': item.fecha_publicacion.isoformat(),
        'url': reverse('mod_detalle_oferta', args=[item.pk]),
        'pending': item.estado == 'pendiente',
    } for item in offer_items]
    items.sort(key=lambda item: item['fecha'], reverse=True)
    items.sort(key=lambda item: not item['pending'])
    return {
        'pendientes': company_count + offer_count,
        'empresas_pendientes': company_count,
        'ofertas_pendientes': offer_count,
        'recientes': [{key: value for key, value in item.items() if key != 'pending'} for item in items[:5]],
    }
