from .models import Curso, Categoria


def crear_curso(form):
    curso = form.save()
    return curso

def listar_cursos():
    return Curso.objects.filter(activo=True)

def dar_de_baja_curso(curso_id):
    curso= Curso.objects.get(id= curso_id)
    curso.activo= False
    curso.save()

def modificar_curso(curso_id, datos):
    curso= Curso.objects.get(id=curso_id)
    curso.nombre = datos.get('nombre', curso.nombre)
    curso.descripcion = datos.get('descripcion', curso.descripcion)
    curso.save()
    return curso

def listar_categorias():
    return Categoria.objects.all()

def crear_categoria(form):
    return form.save()

def modificar_categoria(categoria_id, form):
    categoria = Categoria.objects.get(id=categoria_id)
    categoria.nombre = form.cleaned_data['nombre']
    categoria.save()
    return categoria

def dar_de_baja_categoria(categoria_id):
    categoria = Categoria.objects.get(id=categoria_id)
    categoria.delete()