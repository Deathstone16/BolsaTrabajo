from django.shortcuts import get_object_or_404

from ofertas.models import Oferta
from cursos.models import Curso
from categorias.models import Categoria, TipoOferta
from cursos import services as cursos_services
from usuarios.models import Oferente


def listar_cursos_contexto():
    cursos, resumen = cursos_services.listar_cursos_con_resumen()
    return {
        'cursos': cursos,
        'cursos_presenciales': resumen['presenciales'],
        'cursos_virtuales': resumen['virtuales'],
    }


def obtener_curso(curso_id):
    return get_object_or_404(Curso, id=curso_id)


def listar_categorias_contexto():
    return {'categorias': Categoria.objects.all()}


def listar_empresas_contexto():
    empresas = Oferente.objects.pendientes()
    return {'empresas': empresas, 'total': empresas.count()}


def obtener_empresa(pk):
    return get_object_or_404(Oferente, pk=pk)


def listar_ofertas_contexto(estado=''):
    ofertas = Oferta.objects.all().order_by('-fecha_publicacion')
    if estado:
        ofertas = ofertas.filter(estado=estado)
    return {
        'ofertas': ofertas,
        'filtro_actual': estado,
        'total': Oferta.objects.count(),
        'pendientes': Oferta.objects.filter(estado='pendiente').count(),
        'aprobadas': Oferta.objects.filter(estado='activa').count(),
    }


def obtener_oferta(pk):
    return get_object_or_404(Oferta, pk=pk)


def aprobar_oferta(pk):
    obtener_oferta(pk).aprobar()


def rechazar_oferta(pk):
    obtener_oferta(pk).rechazar()


def finalizar_oferta(pk):
    obtener_oferta(pk).finalizar()


def obtener_tipo_oferta(tipo_id):
    return get_object_or_404(TipoOferta, id=tipo_id)


def listar_tipos_oferta_contexto():
    return {'tipos': TipoOferta.objects.all()}