"""Consulta pública de los cursos activos del IEN."""
from django.shortcuts import get_object_or_404, render
from .models import Curso


def listado(request):
    cursos = Curso.objects.filter(activo=True).select_related('categoria').order_by('nombre')
    return render(request, 'cursos/listado.html', {'cursos': cursos, 'vista_activa': 'cursos'})


def detalle(request, pk):
    curso = get_object_or_404(Curso.objects.select_related('categoria'), pk=pk, activo=True)
    return render(request, 'cursos/detalle.html', {'curso': curso, 'vista_activa': 'cursos'})
