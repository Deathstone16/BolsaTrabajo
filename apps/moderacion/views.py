from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from dataclasses import asdict

from cursos.models import Curso
from categorias.models import Categoria, TipoOferta, Habilidad
from cursos.forms import CursoForm, CategoriaForm
from cursos import services as cursos_services
from usuarios.models import Oferente
from usuarios import services as usuarios_service
from ofertas.models import Oferta
from ofertas.forms import TipoOfertaForm, HabilidadForm
from ofertas import services as ofertas_services
from ofertas.dtos import OfertaDTO

from . import services


def es_staff(user):
    return user.is_authenticated and user.is_staff

staff_required = user_passes_test(es_staff, login_url='/usuarios/login/')


# ============================================================
# CURSOS
# ============================================================

@staff_required
def listar_cursos(request):
    return render(request, 'moderacion/listar_cursos.html',
                  services.listar_cursos_contexto())


@staff_required
def crear_curso(request):
    if request.method == 'POST':
        form = CursoForm(request.POST, request.FILES)
        if form.is_valid():
            cursos_services.crear_curso(form)
            messages.success(request, 'Curso creado correctamente')
            return redirect('mod_listar_cursos')
        else:
            messages.error(request, 'Corregí los errores del formulario')
    else:
        form = CursoForm()
    return render(request, 'moderacion/crear_curso.html', {'form': form})


@staff_required
def modificar_curso(request, curso_id):
    curso = services.obtener_curso(curso_id)
    if request.method == 'POST':
        form = CursoForm(request.POST, request.FILES, instance=curso)
        if form.is_valid():
            cursos_services.modificar_curso(curso_id, form)
            messages.success(request, 'Curso modificado correctamente')
            return redirect('mod_listar_cursos')
        else:
            messages.error(request, 'Corregí los errores del formulario')
    else:
        form = CursoForm(instance=curso)
    return render(request, 'moderacion/modificar_curso.html', {
        'form': form, 'curso': curso,
    })


@staff_required
def dar_de_baja_curso(request, curso_id):
    curso = services.obtener_curso(curso_id)
    if request.method == 'POST':
        cursos_services.dar_de_baja_curso(curso_id)
        messages.success(
            request,
            f"Curso '{curso.nombre}' dado de baja correctamente"
        )
        return redirect('mod_listar_cursos')
    return render(request, 'moderacion/confirmar_baja.html', {'curso': curso})


# ============================================================
# CATEGORÍAS
# ============================================================

@staff_required
def listar_categorias(request):
    return render(request, 'moderacion/listar_categorias.html',
                  services.listar_categorias_contexto())


@staff_required
def crear_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            cursos_services.crear_categoria(form)
            messages.success(request, 'Categoría creada correctamente')
            return redirect('mod_listar_categorias')
        else:
            messages.error(request, 'Corregí los errores del formulario')
    else:
        form = CategoriaForm()
    return render(request, 'moderacion/crear_categoria.html', {'form': form})


@staff_required
def modificar_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            cursos_services.modificar_categoria(categoria_id, form)
            messages.success(request, 'Categoría modificada correctamente')
            return redirect('mod_listar_categorias')
        else:
            messages.error(request, 'Corregí los errores del formulario')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'moderacion/modificar_categoria.html', {
        'form': form, 'categoria': categoria,
    })


@staff_required
def dar_de_baja_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, id=categoria_id)
    if request.method == 'POST':
        nombre = categoria.nombre
        cursos_services.dar_de_baja_categoria(categoria_id)
        messages.success(
            request,
            f"La categoría '{nombre}' fue dada de baja correctamente"
        )
        return redirect('mod_listar_categorias')
    return render(request, 'moderacion/confirmar_baja_categoria.html', {
        'categoria': categoria,
    })


# ============================================================
# EMPRESAS
# ============================================================

@staff_member_required
def listar_empresas(request):
    return render(request, 'moderacion/listar_empresas.html',
                  services.listar_empresas_contexto())


@staff_member_required
def detalle_empresa(request, pk):
    empresa = services.obtener_empresa(pk)
    return render(request, 'moderacion/detalle_empresa.html', {
        'empresa': empresa,
    })


@staff_member_required
def aprobar_empresa(request, pk):
    if request.method == 'POST':
        empresa = services.obtener_empresa(pk)
        usuarios_service.aprobar_empresa(empresa)
    return redirect('mod_listar_empresas')


@staff_member_required
def rechazar_empresa(request, pk):
    if request.method == 'POST':
        empresa = services.obtener_empresa(pk)
        usuarios_service.rechazar_empresa(empresa)
    return redirect('mod_listar_empresas')


# ============================================================
# OFERTAS (moderación)
# ============================================================

@staff_required
def listar_ofertas(request):
    estado = request.GET.get('estado', '')
    return render(request, 'moderacion/ofertas_pendientes.html',
                  services.listar_ofertas_contexto(estado))


@staff_required
def detalle_oferta_json(request, pk):
    oferta = services.obtener_oferta(pk)
    dto = OfertaDTO.desde_modelo(oferta)
    return JsonResponse(asdict(dto))


@staff_required
def aprobar_oferta(request, pk):
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'Método no permitido'},
            status=405
        )
    try:
        services.aprobar_oferta(pk)
        return JsonResponse({'success': True})
    except ValueError as e:
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=400
        )


@staff_required
def rechazar_oferta(request, pk):
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'Método no permitido'},
            status=405
        )
    try:
        services.rechazar_oferta(pk)
        return JsonResponse({'success': True})
    except ValueError as e:
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=400
        )


@staff_required
def finalizar_oferta(request, pk):
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'Método no permitido'},
            status=405
        )
    try:
        services.finalizar_oferta(pk)
        return JsonResponse({'success': True})
    except ValueError as e:
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=400
        )


# TODO: descomentar cuando TipoOferta esté migrado
# ============================================================
# TIPOS DE OFERTA
# ============================================================
#
@staff_required
def listar_tipos_oferta(request):
    return render(request, 'moderacion/listar_tipos_oferta.html',
                  services.listar_tipos_oferta_contexto())

@staff_required
def crear_tipo_oferta(request):
    if request.method == 'POST':
        form = TipoOfertaForm(request.POST)
        if form.is_valid():
            ofertas_services.crear_tipo_oferta(form)
            messages.success(request, 'Tipo de oferta creado correctamente')
            return redirect('mod_listar_tipos_oferta')
        else:
            messages.error(request, 'Corregí los errores del formulario')
    else:
        form = TipoOfertaForm()
    return render(request, 'moderacion/crear_tipo_oferta.html', {'form': form})

@staff_required
def modificar_tipo_oferta(request, tipo_id):
    tipo = services.obtener_tipo_oferta(tipo_id)
    if request.method == 'POST':
        form = TipoOfertaForm(request.POST, instance=tipo)
        if form.is_valid():
            ofertas_services.modificar_tipo_oferta(tipo_id, form)
            messages.success(request, 'Tipo de oferta modificado correctamente')
            return redirect('mod_listar_tipos_oferta')
        else:
            messages.error(request, 'Corregí los errores del formulario')
    else:
        form = TipoOfertaForm(instance=tipo)
    return render(request, 'moderacion/modificar_tipo_oferta.html', {
        'form': form, 'tipo': tipo,
    })

@staff_required
def eliminar_tipo_oferta(request, tipo_id):
    tipo = services.obtener_tipo_oferta(tipo_id)
    if not ofertas_services.puede_eliminar_tipo_oferta(tipo_id):
        messages.error(request, 'No se puede eliminar porque tiene ofertas asociadas.')
        return redirect('mod_listar_tipos_oferta')
    if request.method == 'POST':
        ofertas_services.eliminar_tipo_oferta(tipo_id)
        messages.success(request, f"Tipo de oferta '{tipo.nombre}' eliminado correctamente")
        return redirect('mod_listar_tipos_oferta')
    return render(request, 'moderacion/confirmar_baja_tipo_oferta.html', {'tipo': tipo})

# ============================================================
# HABILIDADES
# ============================================================

@staff_required
def listar_habilidades(request, tipo_id):
    tipo = get_object_or_404(TipoOferta, id=tipo_id)
    habilidades = ofertas_services.listar_habilidades_por_tipo(tipo_id)
    return render(request, 'moderacion/listar_habilidades.html', {
        'tipo': tipo,
        'habilidades': habilidades,
    })


@staff_required
def crear_habilidad(request, tipo_id):
    tipo = get_object_or_404(TipoOferta, id=tipo_id)
    if request.method == 'POST':
        form = HabilidadForm(request.POST)
        if form.is_valid():
            form.instance.tipo_oferta = tipo
            form.save()
            messages.success(request, 'Habilidad creada correctamente')
            return redirect('mod_listar_habilidades', tipo_id=tipo.id)
        messages.error(request, 'Corregí los errores del formulario')
    else:
        form = HabilidadForm()
    return render(request, 'moderacion/crear_habilidad.html', {
        'form': form, 'tipo': tipo,
    })


@staff_required
def modificar_habilidad(request, habilidad_id):
    habilidad = get_object_or_404(Habilidad, id=habilidad_id)
    if request.method == 'POST':
        form = HabilidadForm(request.POST, instance=habilidad)
        if form.is_valid():
            form.save()
            messages.success(request, 'Habilidad modificada correctamente')
            return redirect('mod_listar_habilidades', tipo_id=habilidad.tipo_oferta_id)
        messages.error(request, 'Corregí los errores del formulario')
    else:
        form = HabilidadForm(instance=habilidad)
    return render(request, 'moderacion/modificar_habilidad.html', {
        'form': form, 'habilidad': habilidad,
    })


@staff_required
def eliminar_habilidad(request, habilidad_id):
    habilidad = get_object_or_404(Habilidad, id=habilidad_id)
    tipo_id = habilidad.tipo_oferta_id
    if not ofertas_services.puede_eliminar_habilidad(habilidad_id):
        messages.error(request, 'No se puede eliminar: la habilidad está asociada a una oferta.')
        return redirect('mod_listar_habilidades', tipo_id=tipo_id)
    if request.method == 'POST':
        ofertas_services.eliminar_habilidad(habilidad_id)
        messages.success(request, 'Habilidad eliminada correctamente')
        return redirect('mod_listar_habilidades', tipo_id=tipo_id)
    return render(request, 'moderacion/confirmar_baja_habilidad.html', {'habilidad': habilidad})