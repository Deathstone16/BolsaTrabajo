from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from cursos.models import Curso, Categoria
from cursos.forms import CursoForm, CategoriaForm
from cursos import services as cursos_services
from usuarios.models import Oferente
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from ofertas.models import Oferta, TipoOferta
from ofertas.forms import TipoOfertaForm
from ofertas import services as ofertas_services
from ofertas.dtos import OfertaDTO
from dataclasses import asdict


def es_staff(user):
    return user.is_authenticated and user.is_staff

staff_required = user_passes_test(es_staff, login_url= '/usuarios/login/')

@staff_required
def listar_cursos(request):
    cursos, resumen = cursos_services.listar_cursos_con_resumen()
    return render(request, 'moderacion/listar_cursos.html', {
        'cursos': cursos,
        'cursos_presenciales': resumen['presenciales'],
        'cursos_virtuales': resumen['virtuales'],
    })

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
    curso = get_object_or_404(Curso, id=curso_id)    
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
    return render(request, 'moderacion/modificar_curso.html', {'form': form, 'curso': curso})

@staff_required
def dar_de_baja_curso(request, curso_id):
    if request.method == 'POST':
        cursos_services.dar_de_baja_curso(curso_id)
        curso = get_object_or_404(Curso, id=curso_id)
        messages.success(request, f"Curso '{curso.nombre}' dado de baja correctamente")
        return redirect('mod_listar_cursos')
    curso = get_object_or_404(Curso, id=curso_id)
    return render(request, 'moderacion/confirmar_baja.html', {'curso': curso})

@staff_required
def listar_categorias(request):
    categorias = cursos_services.listar_categorias()
    return render(request, 'moderacion/listar_categorias.html', {'categorias': categorias})

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
    return render(request, 'moderacion/modificar_categoria.html', {'form': form, 'categoria': categoria})

@staff_required
def dar_de_baja_categoria(request, categoria_id):
    if request.method == 'POST':
        cursos_services.dar_de_baja_categoria(categoria_id)
        messages.success(request, f"La categoría '{categoria.nombre}' fue dada de baja correctamente")
        return redirect('mod_listar_categorias')
    categoria = get_object_or_404(Categoria, id=categoria_id)
    return render(request, 'moderacion/confirmar_baja_categoria.html', {'categoria': categoria})


@staff_member_required
def listar_empresas(request):
    empresas = Oferente.objects.filter(estado='pendiente').select_related('usuario').order_by('nombre_empresa')
    return render(request, 'moderacion/listar_empresas.html', {
        'empresas': empresas,
        'total': empresas.count(),
    })


@staff_member_required
def detalle_empresa(request, pk):
    empresa = get_object_or_404(Oferente, pk=pk)
    return render(request, 'moderacion/detalle_empresa.html', {'empresa': empresa})


@staff_member_required
def aprobar_empresa(request, pk):
    if request.method == 'POST':
        empresa = get_object_or_404(Oferente, pk=pk)
        empresa.estado = 'aprobado'
        empresa.save()
        return redirect('mod_listar_empresas')
    return redirect('mod_listar_empresas')


@staff_member_required
def rechazar_empresa(request, pk):
    if request.method == 'POST':
        empresa = get_object_or_404(Oferente, pk=pk)
        empresa.estado = 'rechazado'
        empresa.save()
        return redirect('mod_listar_empresas')
    return redirect('mod_listar_empresas')
# ========== OFERTAS (moderación) ==========

@staff_required
def listar_ofertas(request):
    estado = request.GET.get('estado', '')
    ofertas = Oferta.objects.all().order_by('-fecha_publicacion')
    if estado:
        ofertas = ofertas.filter(estado=estado)

    total = ofertas.count()
    pendientes = Oferta.objects.filter(estado='pendiente').count()
    activas = Oferta.objects.filter(estado='activa').count()

    return render(request, 'moderacion/ofertas_pendientes.html', {
        'ofertas': ofertas,
        'total': total,
        'pendientes': pendientes,
        'aprobadas': activas,
        'filtro_actual': estado,
    })


@staff_required
def detalle_oferta_json(request, pk):
    oferta = get_object_or_404(Oferta, id=pk)
    dto = OfertaDTO.desde_modelo(oferta)
    return JsonResponse(asdict(dto))


@staff_required
def aprobar_oferta(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    oferta = get_object_or_404(Oferta, id=pk)
    try:
        oferta.aprobar()
        return JsonResponse({'success': True})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@staff_required
def rechazar_oferta(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    oferta = get_object_or_404(Oferta, id=pk)
    try:
        oferta.rechazar()
        oferta.motivo_rechazo = request.POST.get('motivo', '')
        oferta.save(update_fields=['motivo_rechazo'])
        return JsonResponse({'success': True})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@staff_required
def finalizar_oferta(request, pk):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    oferta = get_object_or_404(Oferta, id=pk)
    try:
        oferta.finalizar()
        return JsonResponse({'success': True})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ========== TIPOS DE OFERTA ==========

@staff_required
def listar_tipos_oferta(request):
    tipos = ofertas_services.listar_tipos_oferta()
    return render(request, 'moderacion/listar_tipos_oferta.html', {'tipos': tipos})


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
    tipo = get_object_or_404(TipoOferta, id=tipo_id)
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
    return render(request, 'moderacion/modificar_tipo_oferta.html', {'form': form, 'tipo': tipo})


@staff_required
def eliminar_tipo_oferta(request, tipo_id):
    tipo = get_object_or_404(TipoOferta, id=tipo_id)
    if not ofertas_services.puede_eliminar_tipo_oferta(tipo_id):
        messages.error(request, 'No se puede eliminar este tipo de oferta porque tiene ofertas asociadas.')
        return redirect('mod_listar_tipos_oferta')
    if request.method == 'POST':
        ofertas_services.eliminar_tipo_oferta(tipo_id)
        messages.success(request, f"Tipo de oferta '{tipo.nombre}' eliminado correctamente")
        return redirect('mod_listar_tipos_oferta')
    return render(request, 'moderacion/confirmar_baja_tipo_oferta.html', {'tipo': tipo})
