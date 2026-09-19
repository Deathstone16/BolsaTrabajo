"""
Servicios de la capa de moderación.

Funciones que alimentan las vistas del panel de administración
para cursos, categorías, empresas y ofertas.
"""

from django.shortcuts import get_object_or_404
from cursos.models import Curso, Categoria
from usuarios.models import Oferente
from ofertas.models import Oferta
from cursos import services as cursos_services



# ============================================================
# CURSOS
# ============================================================

def listar_cursos_contexto():
    """Construye el contexto del listado de cursos y su resumen por tipo."""
    cursos, resumen = cursos_services.listar_cursos_con_resumen()
    return {
        'cursos': cursos,
        'cursos_presenciales': resumen['presenciales'],
        'cursos_virtuales': resumen['virtuales'],
    }


def obtener_curso(curso_id):
    """Obtiene un curso o responde con HTTP 404 cuando no existe."""
    return get_object_or_404(Curso, id=curso_id)


# ============================================================
# CATEGORÍAS
# ============================================================

def listar_categorias_contexto():
    """Construye el contexto con todas las categorías."""
    return {'categorias': Categoria.objects.all()}


# ============================================================
# EMPRESAS
# ============================================================

def listar_empresas_contexto():
    """Construye el contexto optimizado del listado de empresas."""
    empresas = Oferente.objects.select_related('usuario').order_by('-usuario__date_joined')
    return {
        'empresas': empresas,
        'total': empresas.count(),
    }


def obtener_empresa(pk):
    """Obtiene una empresa o responde con HTTP 404."""
    return get_object_or_404(Oferente, pk=pk)


# ============================================================
# OFERTAS (moderación)
# ============================================================

def listar_ofertas_contexto(estado=''):
    """Construye listado y estadísticas globales de ofertas para moderación."""
    # Base queryset optimizado
    base_qs = Oferta.objects.select_related('empresa__oferente', 'categoria').order_by('-fecha_publicacion')
    
    # Stats globales (SIN filtro) - variables que el template YA usa
    total = Oferta.objects.count()
    pendientes = Oferta.objects.filter(estado='pendiente').count()
    aprobadas = Oferta.objects.filter(estado='activa').count()
    
    # Aplicar filtro solo a la lista
    if estado:
        ofertas = base_qs.filter(estado=estado)
    else:
        ofertas = base_qs
    
    return {
        'ofertas': ofertas,
        'filtro_actual': estado,
        'total': total,
        'pendientes': pendientes,
        'aprobadas': aprobadas,
    }


def obtener_oferta(pk):
    """Obtiene una oferta con sus relaciones principales precargadas."""
    return get_object_or_404(
        Oferta.objects.select_related('empresa__oferente', 'categoria'),
        pk=pk,
    )


def aprobar_oferta(pk):
    """Delega en el modelo la transición de una oferta a activa."""
    obtener_oferta(pk).aprobar()


def rechazar_oferta(pk, motivo=None):
    """Delega en el modelo el rechazo de una oferta y su motivo."""
    obtener_oferta(pk).rechazar(motivo=motivo)


def finalizar_oferta(pk):
    """Delega en el modelo la finalización de una oferta activa."""
    obtener_oferta(pk).finalizar()


