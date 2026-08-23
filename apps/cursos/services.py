"""
Servicios de gestión de cursos y categorías.

CRUD de cursos, categorías y funciones de resumen
estadístico para el panel de administración.
"""

from .models import Curso, Categoria
from django.shortcuts import get_object_or_404

def crear_curso(form):
    """Crea un curso nuevo desde un formulario validado.

    Args:
        form: Formulario CursoForm con datos validados.

    Returns:
        Curso: Instancia del curso creado.
    """
    curso = form.save()
    return curso

def listar_cursos():
    """Devuelve todos los cursos activos."""
    return Curso.objects.filter(activo=True)

def dar_de_baja_curso(curso_id):
    """Desactiva un curso (baja lógica, no elimina).

    Args:
        curso_id (int): ID del curso a dar de baja.
    """
    curso = get_object_or_404(Curso, id=curso_id)
    curso.activo= False
    curso.save()

def modificar_curso(curso_id, datos):
    curso= Curso.objects.get(id=curso_id)
    curso.nombre = datos.get('nombre', curso.nombre)
    curso.descripcion = datos.get('descripcion', curso.descripcion)
    curso.save()
    return curso

def modificar_curso(curso_id, form):
    """Modifica un curso existente con los datos del formulario.

    Args:
        curso_id (int): ID del curso a modificar.
        form: Formulario CursoForm con datos validados.
    """
    curso = get_object_or_404(Curso, id=curso_id) 
    return form.save()

def listar_categorias():
    """Devuelve todas las categorías."""
    return Categoria.objects.all()

def crear_categoria(form):
    """Crea una categoría desde un formulario validado."""
    return form.save()

def modificar_categoria(categoria_id, form):
    """Modifica una categoría existente."""
    categoria = get_object_or_404(Categoria, id=categoria_id)
    return form.save()

def dar_de_baja_categoria(categoria_id):
    """Elimina físicamente una categoría.

    Args:
        categoria_id (int): ID de la categoría a eliminar.

    Returns:
        str: Nombre de la categoría eliminada.
    """
    categoria = get_object_or_404(Categoria, id=categoria_id)
    nombre = categoria.nombre
    categoria.delete()
    return nombre

def listar_cursos_con_resumen():
    """Devuelve cursos activos junto con resumen de cantidades por tipo.

    Returns:
        tuple: (QuerySet de cursos, dict con keys total/presenciales/virtuales/hibridos).
    """
    """Devuelve cursos activos + resumen de tipos."""
    cursos = Curso.objects.filter(activo=True)
    resumen = {
        'total': cursos.count(),
        'presenciales': cursos.filter(tipo='Presencial').count(),
        'virtuales': cursos.filter(tipo='Virtual').count(),
        'hibridos': cursos.filter(tipo='Hibrido').count(),
    }
    return cursos, resumen