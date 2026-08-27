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
    cursos, resumen = cursos_services.listar_cursos_con_resumen()
    return {
        'cursos': cursos,
        'cursos_presenciales': resumen['presenciales'],
        'cursos_virtuales': resumen['virtuales'],
    }


def obtener_curso(curso_id):
    return get_object_or_404(Curso, id=curso_id)


# ============================================================
# CATEGORÍAS
# ============================================================

def listar_categorias_contexto():
    return {'categorias': Categoria.objects.all()}


# ============================================================
# EMPRESAS
# ============================================================

def listar_empresas_contexto():
    empresas = Oferente.objects.pendientes()
    return {
        'empresas': empresas,
        'total': empresas.count(),
    }


def obtener_empresa(pk):
    return get_object_or_404(Oferente, pk=pk)


# ============================================================
# OFERTAS (moderación)
# ============================================================

def listar_ofertas_contexto(estado=''):
    ofertas = Oferta.objects.all().select_related(
        'empresa__oferente', 'categoria'
    )
    if estado:
        ofertas = ofertas.filter(estado=estado)
    return {
        'ofertas': ofertas,
        'filtro_actual': estado,
    }


def obtener_oferta(pk):
    return get_object_or_404(
        Oferta.objects.select_select_related('empresa__oferente', 'categoria'),
        pk=pk,
    )


def aprobar_oferta(pk):
    obtener_oferta(pk).aprobar()


def rechazar_oferta(pk):
    obtener_oferta(pk).rechazar()


def finalizar_oferta(pk):
    obtener_oferta(pk).finalizar()


# TODO: Implementar cuando TipoOferta esté migrado como modelo
# Bloqueado por: falta crear el modelo en ofertas/models.py y generar migración
#
# def listar_tipos_oferta_contexto():
#     return {'tipos': TipoOferta.objects.all()}
#
# def obtener_tipo_oferta(tipo_id):
#     return get_object_or_404(TipoOferta, id=tipo_id)
