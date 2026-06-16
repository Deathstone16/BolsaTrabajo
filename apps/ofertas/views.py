from django.shortcuts import render, redirect
from django.http import JsonResponse
from .forms import OfertaForm
from .services import crear_oferta_laboral, obtener_ofertas_por_empresa, obtener_oferta_por_id, eliminar_oferta_por_id
from usuarios.forms import OferenteForm
from usuarios.decorators import oferente_required


@oferente_required
def crear_oferta(request):

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


@oferente_required
def dashboard_empresa(request):
    
    oferente = request.user.oferente
    ofertas = obtener_ofertas_por_empresa(request.user)
    form_perfil = OferenteForm(instance=oferente)
    form = OfertaForm()

    return render(request, 'Ofertas/home_oferente.html', {
        'oferente': oferente,
        'ofertas': ofertas,
        'form_perfil': form_perfil,
        'form': form,
    })


@oferente_required
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


@oferente_required
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


@oferente_required
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
        'habilidades_requeridas': oferta.habilidades_requeridas,
        'experiencia_requerida': oferta.experiencia_requerida,
        'nivel_educativo': oferta.nivel_educativo,
        'es_confidencial': oferta.es_confidencial,
        'fecha_cierre': oferta.fecha_cierre.strftime('%Y-%m-%d') if oferta.fecha_cierre else '',
    })


@oferente_required
def lista_ofertas_parcial(request):

    ofertas = obtener_ofertas_por_empresa(request.user)

    return render(request, 'Ofertas/_lista-ofertas.html', {
        'ofertas': ofertas,
    })


@oferente_required
def editar_perfil_empresa(request):

    oferente = request.user.oferente

    if request.method == 'POST':
        form = OferenteForm(request.POST, request.FILES, instance=oferente)
        if form.is_valid():
            form.save()
            return redirect('dashboard_empresa#empresa')

    return redirect('dashboard_empresa')