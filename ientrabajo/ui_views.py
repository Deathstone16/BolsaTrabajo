"""Vistas de la interfaz nueva (rediseno de la rama nueva-interfaz-bolsatrabajo).

Corren en paralelo a las vistas de siempre: reutilizan exactamente los mismos
services y modelos, lo unico que cambia es el template que renderizan.
Asi se puede comparar interfaz vieja vs. nueva sin tocar lo que ya funciona.

Cuando el rediseno se apruebe, el paso final es hacer que las vistas originales
rendericen estos templates y borrar este archivo junto con ientrabajo/ui_urls.py.
"""

from django.shortcuts import get_object_or_404, render

from cursos.models import Curso
from ofertas.models import Oferta
from ofertas.services import obtener_ofertas_activas
from usuarios.models import Oferente


def home(request):
    """Portada del rediseno, con ofertas y contadores reales."""
    ofertas_activas = Oferta.objects.filter(estado='activa').select_related('empresa__oferente')
    destacadas = list(ofertas_activas[:3])

    return render(request, 'nueva_ui/home.html', {
        'vista_activa': 'inicio',
        'ofertas_destacadas': destacadas,
        'oferta_destacada': destacadas[0] if destacadas else None,
        'total_ofertas': ofertas_activas.count(),
        'total_empresas': Oferente.objects.aprobados().count(),
        'total_cursos': Curso.objects.count(),
    })


def buscar_empleo(request):
    """Mismo comportamiento que ofertas.views.buscar_empleo, con el template nuevo."""
    busqueda = request.GET.get('q', '')
    modalidad = request.GET.get('modalidad', '')
    experiencia = request.GET.get('experiencia', '')

    ofertas = obtener_ofertas_activas(busqueda, modalidad, experiencia)

    return render(request, 'nueva_ui/buscar_empleo.html', {
        'vista_activa': 'buscar',
        'ofertas': ofertas,
        'busqueda': busqueda,
        'modalidad': modalidad,
        'experiencia': experiencia,
        'modalidad_choices': Oferta.MODALIDAD_CHOICES,
        'experiencia_choices': Oferta.EXPERIENCIA_CHOICES,
        'total': ofertas.count(),
    })


def detalle_oferta(request, pk):
    """Mismo comportamiento que ofertas.views.detalle_oferta_postulante."""
    oferta = get_object_or_404(Oferta, pk=pk, estado='activa')
    habilidades = [h.strip() for h in oferta.habilidades_requeridas.split(',') if h.strip()]

    return render(request, 'nueva_ui/detalle_oferta.html', {
        'vista_activa': 'buscar',
        'oferta': oferta,
        'habilidades': habilidades,
    })
