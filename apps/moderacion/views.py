from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from cursos.models import Curso, Categoria
from cursos.forms import CursoForm, CategoriaForm
from cursos import services as cursos_services

@staff_member_required
def listar_cursos(request):
    cursos = cursos_services.listar_cursos()
    context = {
        'cursos': cursos,
        'cursos_presenciales': cursos.filter(tipo='Presencial').count(),
        'cursos_virtuales': cursos.filter(tipo='Virtual').count(),
    }
    return render(request, 'moderacion/listar_cursos.html', context)

@staff_member_required
def crear_curso(request):
    if request.method == 'POST':
        form = CursoForm(request.POST, request.FILES)
        if form.is_valid():
            cursos_services.crear_curso(form)
            return redirect('mod_listar_cursos')
    else:
        form = CursoForm()
    return render(request, 'moderacion/crear_curso.html', {'form': form})

@staff_member_required
def modificar_curso(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    if request.method == 'POST':
        form = CursoForm(request.POST, request.FILES, instance=curso)
        if form.is_valid():
            form.save()
            return redirect('mod_listar_cursos')
    else:
        form = CursoForm(instance=curso)
    return render(request, 'moderacion/modificar_curso.html', {'form': form, 'curso': curso})

@staff_member_required
def dar_de_baja_curso(request, curso_id):
    if request.method == 'POST':
        cursos_services.dar_de_baja_curso(curso_id)
        return redirect('mod_listar_cursos')
    curso = get_object_or_404(Curso, id=curso_id)
    return render(request, 'moderacion/confirmar_baja.html', {'curso': curso})

@staff_member_required
def listar_categorias(request):
    categorias = cursos_services.listar_categorias()
    return render(request, 'moderacion/listar_categorias.html', {'categorias': categorias})

@staff_member_required
def crear_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            cursos_services.crear_categoria(form)
            return redirect('mod_listar_categorias')
    else:
        form = CategoriaForm()
    return render(request, 'moderacion/crear_categoria.html', {'form': form})

@staff_member_required
def modificar_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            cursos_services.modificar_categoria(categoria_id, form)
            return redirect('mod_listar_categorias')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'moderacion/modificar_categoria.html', {'form': form, 'categoria': categoria})

@staff_member_required
def dar_de_baja_categoria(request, categoria_id):
    if request.method == 'POST':
        cursos_services.dar_de_baja_categoria(categoria_id)
        return redirect('mod_listar_categorias')
    categoria = get_object_or_404(Categoria, id=categoria_id)
    return render(request, 'moderacion/confirmar_baja_categoria.html', {'categoria': categoria})