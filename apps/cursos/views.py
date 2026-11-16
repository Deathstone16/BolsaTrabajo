"""Consulta pública de los cursos activos del IEN."""
from django.shortcuts import get_object_or_404, render
from .forms import CursoFiltroForm
from .models import Curso


def listado(request):
    cursos = Curso.objects.filter(activo=True).select_related('categoria').order_by('nombre')
    filtros = CursoFiltroForm(request.GET)
    if filtros.is_valid():
        valores = filtros.cleaned_data
        if valores['q']:
            cursos = cursos.filter(nombre__icontains=valores['q'])
        if valores['categoria']:
            cursos = cursos.filter(categoria=valores['categoria'])
        if valores['modalidad']:
            cursos = cursos.filter(tipo=valores['modalidad'])
        if valores['duracion']:
            cursos = cursos.filter(duracion=valores['duracion'])
    else:
        cursos = cursos.none()
    return render(request, 'cursos/listado.html', {
        'cursos': cursos,
        'vista_activa': 'cursos',
        'filtros': filtros,
        'hay_filtros': any(request.GET.get(nombre, '').strip() for nombre in filtros.fields),
        'total_resultados': cursos.count(),
    })


def detalle(request, pk):
    curso = get_object_or_404(Curso.objects.select_related('categoria'), pk=pk, activo=True)
    return render(request, 'cursos/detalle.html', {'curso': curso, 'vista_activa': 'cursos'})
