"""Vistas MVT para publicar, administrar y consultar ofertas laborales."""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from .forms import OfertaForm
from .models import Oferta
from .services import crear_oferta_laboral, obtener_ofertas_por_empresa, obtener_oferta_por_id, eliminar_oferta_por_id, obtener_ofertas_activas
from usuarios.forms import OferenteForm
from usuarios.services import obtener_url_contacto
from usuarios import services as usuarios_service
from usuarios.decorators import oferente_required, oferente_validado_required
from .dtos import OfertaDTO
from dataclasses import asdict

@oferente_required
def validacion_pendiente(request):
    """Muestra a la empresa el estado pendiente de validación de su perfil."""
    oferente = request.user.oferente
    email_contacto_url = obtener_url_contacto(request.user.email)
    return render(request, 'Ofertas/validacion_pendiente.html', {
        'email_contacto_url': email_contacto_url,
        'oferente': oferente,
    })

@oferente_validado_required
def crear_oferta(request):
    """Crea una oferta desde POST y devuelve JSON cuando la petición es AJAX."""

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
    """Renderiza el panel de la empresa con perfil, ofertas y formulario."""
    
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


@oferente_validado_required
def editar_oferta(request, pk):
    """Actualiza una oferta propia editable y la devuelve a revisión."""
    oferta = obtener_oferta_por_id(pk)

    if not oferta or oferta.empresa != request.user or not oferta.puede_editarse():
        return redirect('dashboard_empresa')

    if request.method == 'POST':
        form = OfertaForm(request.POST, instance=oferta)
        if form.is_valid():
            oferta = form.save(commit=False)
            oferta.estado = 'pendiente'
            oferta.save()
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
    """Elimina por POST una oferta perteneciente a la empresa autenticada."""
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
    """Devuelve como JSON los datos de una oferta para completar el modal."""
    oferta = obtener_oferta_por_id(pk)

    if not oferta or oferta.empresa != request.user:
        return JsonResponse({'error': 'No encontrada'}, status=404)

    dto = OfertaDTO.desde_modelo(oferta)
    return JsonResponse(asdict(dto))

@oferente_validado_required
def lista_ofertas_parcial(request):
    """Renderiza solamente la lista usada para refrescar el panel por AJAX."""

    ofertas = obtener_ofertas_por_empresa(request.user)

    return render(request, 'Ofertas/_lista-ofertas.html', {
        'ofertas': ofertas,
        'oferente': request.user.oferente, #temporalmente necesario para el template, se puede refactorizar para no necesitarlo
    })


@oferente_required
def editar_perfil_empresa(request):
    """Actualiza el perfil oferente y reenvía a revisión uno rechazado."""
    oferente = request.user.oferente
    if request.method == 'POST':
        form = OferenteForm(request.POST, request.FILES, instance=oferente)
        if form.is_valid():
            form.save()
            if oferente.estado_validacion == 'rechazado':
                usuarios_service.enviar_a_revision(oferente)
            return redirect(reverse('dashboard_empresa') + '#empresa')
    else:
        form = OferenteForm(instance=oferente)
    return render(request, 'Ofertas/editar-perfil.html', {'form': form, 'oferente': oferente})


def detalle_oferta_postulante(request, pk):
    """Muestra el detalle público de una oferta activa."""
    oferta = get_object_or_404(Oferta, pk=pk, estado='activa')
    habilidades = [h.strip() for h in oferta.habilidades_requeridas.split(',') if h.strip()]
    return render(request, 'nueva_ui/detalle_oferta.html', {
        'vista_activa': 'buscar',
        'oferta': oferta,
        'habilidades': habilidades,
    })


def buscar_empleo(request):
    """Lista ofertas activas aplicando filtros recibidos por query string."""
    busqueda = request.GET.get('q', '')
    modalidad = request.GET.get('modalidad', '')
    experiencia = request.GET.get('experiencia', '')

    ofertas = obtener_ofertas_activas(busqueda, modalidad, experiencia)

    return render(request, 'nueva_ui/buscar_empleo.html', {
        'vista_activa': 'buscar',
        'ofertas': ofertas,
        'busqueda': busqueda,
        'modalidad': modalidad,
        'experiencia': experiencia,
        'modalidad_choices': Oferta.MODALIDAD_CHOICES,
        'experiencia_choices': Oferta.EXPERIENCIA_CHOICES,
        'total': ofertas.count(),
    })
