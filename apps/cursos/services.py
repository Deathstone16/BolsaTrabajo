from .models import Curso, Categoria
from django.shortcuts import get_object_or_404

def crear_curso(form):
    curso = form.save()
    return curso

def listar_cursos():
    return Curso.objects.filter(activo=True)

def dar_de_baja_curso(curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    curso.activo= False
    curso.save(update_fields=['activo'])

def modificar_curso(curso_id, form):
    curso = get_object_or_404(Curso, id=curso_id) 
    return form.save()

def listar_categorias():
    return Categoria.objects.all()

def crear_categoria(form):
    return form.save()

def modificar_categoria(categoria_id, form):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    return form.save()

def dar_de_baja_categoria(categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    categoria.delete()

def listar_cursos_con_resumen():
    """Devuelve cursos activos + resumen de tipos."""
    cursos = Curso.objects.filter(activo=True)
    resumen = {
        'total': cursos.count(),
        'presenciales': cursos.filter(tipo='Presencial').count(),
        'virtuales': cursos.filter(tipo='Virtual').count(),
        'hibridos': cursos.filter(tipo='Hibrido').count(),
    }
    return cursos, resumen