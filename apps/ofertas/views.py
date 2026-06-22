from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from .forms import OfertaForm
from .services import crear_oferta_laboral, obtener_ofertas_por_empresa, obtener_oferta_por_id, eliminar_oferta_por_id
from usuarios.forms import OferenteForm
from usuarios.service import obtener_url_contacto
from usuarios.decorators import oferente_required, oferente_validado_required
from .dtos import OfertaDTO
from dataclasses import asdict

@oferente_required
def validacion_pendiente(request):
    email_contacto_url = obtener_url_contacto(request.user.email)
    return render(request, 'Ofertas/validacion_pendiente.html', {
        'email_contacto_url': email_contacto_url,
    })

@oferente_validado_required
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


@oferente_validado_required
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


@oferente_validado_required
def editar_oferta(request, pk):
    oferta = obtener_oferta_por_id(pk)

    if not oferta or oferta.empresa != request.user or not oferta.puede_editarse():
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


@oferente_validado_required
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

@oferente_validado_required
def datos_oferta(request, pk):
    oferta = obtener_oferta_por_id(pk)

    if not oferta or oferta.empresa != request.user:
        return JsonResponse({'error': 'No encontrada'}, status=404)

    dto = OfertaDTO.desde_modelo(oferta)
    return JsonResponse(asdict(dto))

@oferente_validado_required
def lista_ofertas_parcial(request):

    ofertas = obtener_ofertas_por_empresa(request.user)

    return render(request, 'Ofertas/_lista-ofertas.html', {
        'ofertas': ofertas,
    })


@oferente_validado_required
def editar_perfil_empresa(request):

    oferente = request.user.oferente

    if request.method == 'POST':
        form = OferenteForm(request.POST, request.FILES, instance=oferente)
        if form.is_valid():
            form.save()
            return redirect(reverse('dashboard_empresa') + '#empresa')

    return redirect('dashboard_empresa')