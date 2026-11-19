"""Consulta pública de los cursos activos del IEN."""
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from .forms import CursoFiltroForm
from .models import Curso


def listado(request):
    cursos = Curso.objects.filter(activo=True).select_related('categoria').order_by('nombre', 'pk')
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
    paginador = Paginator(cursos, 12)
    pagina = paginador.get_page(request.GET.get('page'))
    parametros = request.GET.copy()
    parametros.pop('page', None)
    return render(request, 'cursos/listado.html', {
        'cursos': pagina.object_list,
        'pagina': pagina,
        'paginas': paginador.get_elided_page_range(pagina.number, on_each_side=1, on_ends=1),
        'pagination_query': parametros.urlencode(),
        'vista_activa': 'cursos',
        'filtros': filtros,
        'hay_filtros': any(request.GET.get(nombre, '').strip() for nombre in filtros.fields),
        'total_resultados': paginador.count,
    })


def detalle(request, pk):
    curso = get_object_or_404(Curso.objects.select_related('categoria'), pk=pk, activo=True)
    return render(request, 'cursos/detalle.html', {'curso': curso, 'vista_activa': 'cursos'})
