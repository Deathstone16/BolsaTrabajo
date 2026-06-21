from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import OfertaForm
from .models import Oferta
from .services import crear_oferta_laboral, obtener_ofertas_por_empresa, obtener_oferta_por_id, eliminar_oferta_por_id, obtener_ofertas_activas
from usuarios.forms import OferenteForm
from django.http import JsonResponse


@login_required
def crear_oferta(request):
    es_oferente = hasattr(request.user, 'oferente')
    if not es_oferente:
        return redirect('home')

    if request.method == 'POST':
        form = OfertaForm(request.POST)
        if form.is_valid():
            oferta = crear_oferta_laboral(request.user, form)
            es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if es_ajax:
                return JsonResponse({'success': True, 'id': oferta.id})
            return redirect('dashboard_empresa')
        else:
            es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if es_ajax:
                return JsonResponse({'success': False, 'errors': form.errors})

    return redirect('dashboard_empresa')


@login_required
def dashboard_empresa(request):
    if not hasattr(request.user, 'oferente'):
        return redirect('home')

    oferente = request.user.oferente
    ofertas = obtener_ofertas_por_empresa(request.user)
    form_perfil = OferenteForm(instance=oferente)
    form = OfertaForm()

    return render(request, 'Ofertas/home_oferente.html', {
        'oferente': oferente,
        'ofertas': ofertas,
        'form_perfil': form_perfil,
        'form': form,
        'experiencia_choices': Oferta.EXPERIENCIA_CHOICES,
    })


@login_required
def editar_oferta(request, pk):
    oferta = obtener_oferta_por_id(pk)

    if not oferta or oferta.empresa != request.user:
        return redirect('dashboard_empresa')

    if request.method == 'POST':
        form = OfertaForm(request.POST, instance=oferta)
        if form.is_valid():
            form.save()
            es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if es_ajax:
                return JsonResponse({'success': True})
            return redirect('dashboard_empresa')
        else:
            es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if es_ajax:
                return JsonResponse({'success': False, 'errors': form.errors})

    return redirect('dashboard_empresa')


@login_required
def eliminar_oferta(request, pk):
    oferta = obtener_oferta_por_id(pk)

    if not oferta or oferta.empresa != request.user:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    if request.method == 'POST':
        eliminar_oferta_por_id(pk)
        es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if es_ajax:
            return JsonResponse({'success': True})
        return redirect('dashboard_empresa')

    return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def datos_oferta(request, pk):
    oferta = obtener_oferta_por_id(pk)

    if not oferta or oferta.empresa != request.user:
        return JsonResponse({'error': 'No encontrada'}, status=404)

    return JsonResponse({
        'titulo': oferta.titulo,
        'nombre_puesto': oferta.nombre_puesto,
        'categoria': oferta.categoria_id,
        'ubicacion': oferta.ubicacion,
        'modalidad': oferta.modalidad,
        'descripcion': oferta.descripcion,
        'requisitos': oferta.requisitos,
        'habilidades_requeridas': oferta.habilidades_requeridas,
        'experiencia_requerida': oferta.experiencia_requerida,
        'nivel_educativo': oferta.nivel_educativo,
        'es_confidencial': oferta.es_confidencial,
        'fecha_cierre': oferta.fecha_cierre.strftime('%Y-%m-%d') if oferta.fecha_cierre else '',
    })


@login_required
def lista_ofertas_parcial(request):
    if not hasattr(request.user, 'oferente'):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    ofertas = obtener_ofertas_por_empresa(request.user)

    return render(request, 'Ofertas/_lista-ofertas.html', {
        'ofertas': ofertas,
    })


@login_required
def editar_perfil_empresa(request):
    if not hasattr(request.user, 'oferente'):
        return redirect('home')

    oferente = request.user.oferente

    if request.method == 'POST':
        form = OferenteForm(request.POST, request.FILES, instance=oferente)
        if form.is_valid():
            form.save()
            return redirect('dashboard_empresa#empresa')

    return redirect('dashboard_empresa')


def detalle_oferta_postulante(request, pk):
    oferta = get_object_or_404(Oferta, pk=pk, estado='activa')
    habilidades = [h.strip() for h in oferta.habilidades_requeridas.split(',') if h.strip()]
    return render(request, 'Ofertas/detalle_oferta.html', {'oferta': oferta, 'habilidades': habilidades})


def buscar_empleo(request):
    busqueda = request.GET.get('q', '')
    modalidad = request.GET.get('modalidad', '')
    experiencia = request.GET.get('experiencia', '')

    ofertas = obtener_ofertas_activas(busqueda, modalidad, experiencia)

    return render(request, 'Ofertas/buscar_empleo.html', {
        'ofertas': ofertas,
        'busqueda': busqueda,
        'modalidad': modalidad,
        'experiencia': experiencia,
        'modalidad_choices': Oferta.MODALIDAD_CHOICES,
        'experiencia_choices': Oferta.EXPERIENCIA_CHOICES,
        'total': ofertas.count(),
    })