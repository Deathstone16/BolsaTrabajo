"""Vistas de registro, autenticación, perfiles y recuperación de acceso."""

from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from ia.profile_skills import split_profile_skills

from .forms import (
    RegistroPostulanteForm,
    RegistroOferenteForm,
    LoginForm,
    DatosPersonalesForm,
    PasswordResetRequestForm,
    SetPasswordForm,
    CargaCVForm,
)
from .decorators import postulante_required, oferente_required
from .models import Oferente
from . import services
from .uploads import cv_enabled_formats
from django.views.decorators.http import require_POST


#vistas
def registro(request):
    """Registra postulantes u oferentes según el rol elegido."""
    tipo = request.GET.get('tipo', 'postulante')
    FormClass = RegistroOferenteForm if tipo == 'oferente' else RegistroPostulanteForm
    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            if tipo == 'oferente':
                services.registrar_oferente(
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password1'],
                    nombre_empresa=form.cleaned_data['nombre_empresa'],
                    cuit=form.cleaned_data['cuit'],
                )
            else:
                services.registrar_postulante(
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password1'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                )
            if tipo == 'oferente':
                return redirect(reverse('registro_exitoso') + '?tipo=oferente')
            return redirect('registro_exitoso')
    else:
        form = FormClass()
    return render(request, 'usuarios/registro.html', {'form': form, 'tipo': tipo})
    
    
    
    


def registro_exitoso(request):
    """Confirma el alta y explica la revisión pendiente de las empresas."""
    if request.GET.get('tipo') == 'oferente':
        return render(request, 'usuarios/exito.html', {
            'titulo': 'Tu empresa quedó en revisión',
            'mensaje': 'Tu cuenta fue creada y tu empresa quedó pendiente de validación por el equipo del IEN. Cuando sea aprobada, vas a poder acceder al panel de empresa y publicar ofertas laborales.',
            'detalle_mensaje': 'Podés iniciar sesión para consultar el estado de la revisión.',
            'pendiente_validacion': True,
            'link_url': reverse('login'),
            'link_texto': 'Consultar estado',
        })
    return render(request, 'usuarios/exito.html', {
        'titulo': '¡Cuenta creada!',
        'mensaje': 'Tu cuenta fue creada exitosamente. Ya podés iniciar sesión.',
        'link_url': reverse('login'),
        'link_texto': 'Iniciar sesión',
    })


def login_view(request):
    """Autentica al usuario y redirige hacia su pantalla correspondiente."""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            if services.autenticar_usuario(request, email, password):
                if services.es_oferente(request.user):
                    return redirect('dashboard_empresa')
                return redirect('home')
            else:
                form.add_error(None, 'Email o contraseña incorrectos.')
    else:
        form = LoginForm()

    return render(request, 'usuarios/login.html', {'form': form})


@require_POST
def logout_view(request):
    """Cierra la sesión actual aceptando únicamente solicitudes POST."""
    services.cerrar_sesion(request)
    return redirect('login')


@login_required
@postulante_required
def datos_personales(request):
    """Permite al postulante consultar y actualizar sus datos personales."""
    postulante = request.user.postulante

    if request.method == 'POST':
        form = DatosPersonalesForm(request.POST, instance=postulante)
        if form.is_valid():
            services.actualizar_datos_postulante(request.user, form)
            return redirect('datos_personales_exitoso')
    else:
        form = DatosPersonalesForm(instance=postulante, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })

    return render(request, 'usuarios/datos_personales.html', {'form': form})


@login_required
@postulante_required
def perfil_oferente(request, pk):
    """Muestra el perfil público de una empresa aprobada."""
    oferente = get_object_or_404(Oferente, pk=pk)
    ofertas = oferente.usuario.oferta_set.filter(estado='activa')
    return render(request, 'Ofertas/perfil_oferente_publico.html', {
        'oferente': oferente,
        'ofertas': ofertas,
    })


def datos_personales_exitoso(request):
    """Confirma la actualización de los datos personales."""
    return render(request, 'usuarios/exito.html', {
        'titulo': '¡Datos guardados!',
        'mensaje': 'Tu información personal fue actualizada correctamente.',
        'link_url': reverse('datos_personales'),
        'link_texto': 'Volver a mis datos',
    })


# ─── Recuperación de contraseña ───────────────────────────────────────────────

def password_reset_request(request):
    """Solicita un enlace de recuperación sin revelar si el email existe."""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            usuario = form.get_usuario()
            if usuario is not None:
                services.enviar_email_recuperacion(usuario, request)
            return redirect('recuperacion-enviada')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'usuarios/recuperar_contrasena.html', {'form': form})


def recuperacion_enviada(request):
    """Informa que la solicitud de recuperación fue procesada."""
    return render(request, 'usuarios/recuperar_enviado.html')


def password_reset_confirm(request, uidb64, token):
    """Valida el token y permite definir una contraseña nueva."""
    usuario = services.validar_token_recuperacion(uidb64, token)

    if usuario is None:
        return render(request, 'usuarios/token_invalido.html')

    if request.method == 'POST':
        form = SetPasswordForm(user=usuario, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('contrasena-restablecida')
    else:
        form = SetPasswordForm(user=usuario)

    return render(request, 'usuarios/restablecer_contrasena.html', {
        'form':   form,
        'uidb64': uidb64,
        'token':  token,
    })


def contrasena_restablecida(request):
    """Confirma que la contraseña fue restablecida."""
    return render(request, 'usuarios/contrasena_exitosa.html')


@login_required
@postulante_required
def mi_perfil(request):
    """Muestra perfil, rol y herramientas propias del usuario autenticado."""
    postulante = request.user.postulante
    # El último análisis permite ofrecer el resultado al volver al perfil.
    ultimo_analisis = postulante.analisis_cv.filter(version_cv_id=postulante.cv_version_actual_id).first() if postulante.cv_version_actual_id else None
    perfil_cv = getattr(postulante, 'perfil_ia', None)
    if perfil_cv and perfil_cv.cv_version_id != postulante.cv_version_actual_id:
        perfil_cv = None
    _, habilidades_blandas = split_profile_skills(perfil_cv.contenido if perfil_cv else {})
    from ia.profile_summary import visible_profile_summary
    resumen_profesional = visible_profile_summary(perfil_cv.contenido) if perfil_cv else None

    if request.method == 'POST':
        _ = request.FILES
        if getattr(request, '_upload_limit_exceeded', None):
            mensaje = 'La solicitud supera el tamaño máximo permitido. El archivo no se guardó.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'mensaje': mensaje}, status=413)
            messages.error(request, mensaje)
            return redirect('mi_perfil')
        if request.FILES.get('foto'):
            try:
                services.guardar_foto_postulante(postulante, request.FILES['foto'])
            except Exception as exc:
                mensaje = exc.messages[0] if hasattr(exc, 'messages') else 'No se pudo procesar la foto.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'mensaje': mensaje}, status=400)
                messages.error(request, mensaje)
                return redirect('mi_perfil')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'mensaje': 'Foto de perfil actualizada.'})
            messages.success(request, 'Foto de perfil actualizada.')
            return redirect('mi_perfil')
        form = CargaCVForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                version = services.cargar_cv(postulante, form.cleaned_data['cv'])
            except Exception as exc:
                mensaje = exc.messages[0] if hasattr(exc, 'messages') else 'No se pudo guardar el CV.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'mensaje': mensaje}, status=400)
                messages.error(request, mensaje)
                return redirect('mi_perfil')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'mensaje': 'CV cargado con éxito. Analizá esta versión para volver a calcular compatibilidades.', 'version_cv_id': version.pk, 'version_cv_numero': version.numero, 'nombre_cv': version.nombre_original})
            messages.success(request, 'CV cargado con éxito.')
            return redirect('mi_perfil')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errores = form.errors.get('cv', [])
                return JsonResponse({'success': False, 'mensaje': errores[0] if errores else 'Error al cargar el CV.'})
    else:
        form = CargaCVForm()

    return render(request, 'usuarios/mi_perfil.html', {
        'postulante': postulante,
        'form': form,
        'ultimo_analisis': ultimo_analisis,
        'perfil_cv': perfil_cv,
        'resumen_profesional': resumen_profesional,
        'habilidades_blandas': habilidades_blandas,
        'version_cv_actual': postulante.cv_version_actual,
        'cv_formatos': cv_enabled_formats(),
    })


@login_required
@postulante_required
def descargar_cv(request, version_id):
    """Entrega un snapshot privado únicamente a su propietario."""
    from django.http import FileResponse
    from ia.models import CVVersion
    version = get_object_or_404(CVVersion, pk=version_id, postulante=request.user.postulante)
    response = FileResponse(version.archivo.open('rb'), as_attachment=True, filename=version.nombre_original)
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Type'] = 'application/octet-stream'
    return response


@login_required
@postulante_required
def eliminar_cv(request):
    """Elimina por POST el CV del postulante autenticado."""
    if request.method == 'POST':
        services.eliminar_cv(request.user.postulante)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'mensaje': 'CV eliminado.'})
        messages.success(request, 'CV eliminado correctamente.')
    return redirect('mi_perfil')
