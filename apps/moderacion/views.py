"""Vistas exclusivas del personal para moderar contenido de la plataforma."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages

from cursos.models import Curso
from categorias.models import Categoria, Habilidad
from cursos.forms import CursoForm, CategoriaForm
from cursos import services as cursos_services
from usuarios.models import Oferente
from usuarios import services as usuarios_service
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from ofertas.models import Oferta
from ofertas.forms import HabilidadForm
from ofertas import services as ofertas_services
from .forms import RechazarEmpresaForm
from . import services



def es_staff(user):
    """Indica si el usuario autenticado pertenece al personal autorizado."""
    return user.is_authenticated and user.is_staff

staff_required = user_passes_test(es_staff, login_url='/usuarios/login/')


# ============================================================
# CURSOS
# ============================================================

@staff_required
def listar_cursos(request):
    """Muestra el listado y resumen de cursos administrables."""
    return render(request, 'moderacion/listar_cursos.html',
                  services.listar_cursos_contexto())


@staff_required
def crear_curso(request):
    """Crea un curso a partir de un formulario multipart válido."""
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
    """Edita un curso existente identificado por ``curso_id``."""
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
    """Confirma y ejecuta la baja lógica de un curso."""
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
    """Muestra las categorías administrables."""
    return render(request, 'moderacion/listar_categorias.html',
                  services.listar_categorias_contexto())


@staff_required
def crear_categoria(request):
    """Crea una categoría de cursos y ofertas."""
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
    """Modifica el nombre de una categoría existente."""
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
    """Confirma y elimina una categoría sin relaciones protegidas."""
    categoria = get_object_or_404(Categoria, id=categoria_id)
    if request.method == 'POST':
        nombre = categoria.nombre
        eliminada = cursos_services.dar_de_baja_categoria(categoria_id)
        if eliminada:
            messages.success(
                request,
                f"La categoría '{nombre}' fue dada de baja correctamente"
            )
        else:
            messages.error(
                request,
                "No se puede eliminar una categoría con cursos, ofertas o habilidades asociadas."
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
    """Muestra las empresas y sus estados de validación."""
    return render(request, 'moderacion/listar_empresas.html',
                  services.listar_empresas_contexto())


@staff_member_required
def detalle_empresa(request, pk):
    """Presenta la información de una empresa para su revisión."""
    empresa = services.obtener_empresa(pk)
    return render(request, 'moderacion/detalle_empresa.html', {
        'empresa': empresa,
    })


@staff_member_required
def aprobar_empresa(request, pk):
    """Aprueba por POST el perfil de una empresa."""
    if request.method == 'POST':
        empresa = services.obtener_empresa(pk)
        usuarios_service.aprobar_empresa(empresa)
    return redirect('mod_listar_empresas')


@staff_member_required
def rechazar_empresa(request, pk):
    """Rechaza una empresa y registra el motivo ingresado."""
    empresa = services.obtener_empresa(pk)
    if request.method == 'POST':
        form = RechazarEmpresaForm(request.POST)
        if form.is_valid():
            motivo = form.cleaned_data['motivo_rechazo']
            usuarios_service.rechazar_empresa(empresa, motivo=motivo)
            messages.success(request, f"Empresa '{empresa.nombre_empresa}' rechazada.")
            return redirect('mod_listar_empresas')
    else:
        form = RechazarEmpresaForm()
    return render(request, 'moderacion/rechazar_empresa.html', {
        'empresa': empresa,
        'form': form,
    })


# ============================================================
# OFERTAS (moderación)
# ============================================================

@staff_required
def listar_ofertas(request):
    """Lista ofertas moderables con un filtro opcional de estado."""
    estado = request.GET.get('estado', '')
    return render(request, 'moderacion/ofertas_pendientes.html',
                  services.listar_ofertas_contexto(estado))


@staff_required
def detalle_oferta(request, pk):
    """Presenta los datos completos de una oferta para su moderación."""
    oferta = services.obtener_oferta(pk)
    return render(request, 'moderacion/detalle_oferta.html', {
        'oferta': oferta,
        'habilidades_duras': [h.strip() for h in (oferta.habilidades_duras or "").split(",") if h.strip()],
        'habilidades_blandas': [h.strip() for h in (oferta.habilidades_blandas or "").split(",") if h.strip()],
    })

@staff_required
def aprobar_oferta(request, pk):
    """Aprueba una oferta pendiente y vuelve a su detalle."""
    if request.method == 'POST':
        try:
            services.aprobar_oferta(pk)
            messages.success(request, 'Oferta aprobada correctamente.')
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('mod_detalle_oferta', pk=pk)

@staff_required
def rechazar_oferta(request, pk):
    """Rechaza una oferta; GET muestra página con motivo, POST la procesa."""
    oferta = services.obtener_oferta(pk)
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()
        if not motivo:
            messages.error(request, 'Se requiere un motivo para rechazar la oferta.')
            return render(request, 'moderacion/rechazar_oferta.html', {'oferta': oferta, 'motivo': motivo})
        try:
            services.rechazar_oferta(pk, motivo=motivo)
            messages.success(request, 'Oferta rechazada.')
        except ValueError as e:
            messages.error(request, str(e))
        return redirect('mod_detalle_oferta', pk=pk)
    return render(request, 'moderacion/rechazar_oferta.html', {'oferta': oferta})

@staff_required
def finalizar_oferta(request, pk):
    """Da de baja una oferta activa y vuelve a su detalle."""
    if request.method == 'POST':
        try:
            services.finalizar_oferta(pk)
            messages.success(request, 'Oferta dada de baja.')
        except ValueError as e:
            messages.error(request, str(e))
    return redirect('mod_detalle_oferta', pk=pk)
# ============================================================
# HABILIDADES
# ============================================================

@staff_required
def listar_habilidades(request, categoria_id):
    """Lista las habilidades asociadas a una categoría."""
    categoria = get_object_or_404(Categoria, id=categoria_id)
    habilidades = ofertas_services.listar_habilidades_por_tipo(categoria_id)
    return render(request, 'moderacion/listar_habilidades.html', {
        'categoria': categoria,
        'habilidades': habilidades,
    })


@staff_required
def crear_habilidad(request, categoria_id):
    """Crea una habilidad dentro de la categoría indicada."""
    categoria = get_object_or_404(Categoria, id=categoria_id)
    if request.method == 'POST':
        form = HabilidadForm(request.POST, instance=Habilidad(categoria=categoria))
        if form.is_valid():
            form.save()
            messages.success(request, 'Habilidad creada correctamente')
            return redirect('mod_listar_habilidades', categoria_id=categoria.id)
        messages.error(request, 'Corregí los errores del formulario')
    else:
        form = HabilidadForm()
    return render(request, 'moderacion/crear_habilidad.html', {
        'form': form, 'categoria': categoria,
    })


@staff_required
def modificar_habilidad(request, habilidad_id):
    """Modifica una habilidad conservando su categoría."""
    habilidad = get_object_or_404(Habilidad, id=habilidad_id)
    if request.method == 'POST':
        form = HabilidadForm(request.POST, instance=habilidad)
        if form.is_valid():
            form.save()
            messages.success(request, 'Habilidad modificada correctamente')
            return redirect('mod_listar_habilidades', categoria_id=habilidad.categoria_id)
        messages.error(request, 'Corregí los errores del formulario')
    else:
        form = HabilidadForm(instance=habilidad)
    return render(request, 'moderacion/modificar_habilidad.html', {
        'form': form, 'habilidad': habilidad,
    })


@staff_required
def eliminar_habilidad(request, habilidad_id):
    """Elimina una habilidad cuando ninguna oferta la está utilizando."""
    habilidad = get_object_or_404(Habilidad, id=habilidad_id)
    categoria_id = habilidad.categoria_id
    if not ofertas_services.puede_eliminar_habilidad(habilidad_id):
        messages.error(request, 'No se puede eliminar: la habilidad está asociada a una oferta.')
        return redirect('mod_listar_habilidades', categoria_id=categoria_id)
    if request.method == 'POST':
        ofertas_services.eliminar_habilidad(habilidad_id)
        messages.success(request, 'Habilidad eliminada correctamente')
        return redirect('mod_listar_habilidades', categoria_id=categoria_id)
    return render(request, 'moderacion/confirmar_baja_habilidad.html', {'habilidad': habilidad})
