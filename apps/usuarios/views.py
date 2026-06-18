from functools import wraps

from django.shortcuts import redirect, render
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from .forms import RegistroPostulanteForm, RegistroOferenteForm, LoginForm, DatosPersonalesForm, OferenteForm
from . import service


#decoradores 

def requiere_oferente(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not service.es_oferente(request.user):
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def requiere_postulante(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not service.es_postulante(request.user):
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


#vistas

def registro(request):
    tipo = request.GET.get('tipo', 'postulante')
    FormClass = RegistroOferenteForm if tipo == 'oferente' else RegistroPostulanteForm

    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            form.save()
            return redirect('registro_exitoso')
    else:
        form = FormClass()

    return render(request, 'usuarios/registro.html', {'form': form, 'tipo': tipo})


def registro_exitoso(request):
    return render(request, 'usuarios/exito.html', {
        'titulo': '¡Cuenta creada!',
        'mensaje': 'Tu cuenta fue creada exitosamente. Ya podés iniciar sesión.',
        'link_url': reverse('login'),
        'link_texto': 'Iniciar sesión',
    })


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            if service.autenticar_usuario(request, email, password):
                return redirect('home')
            else:
                form.add_error(None, 'Email o contraseña incorrectos.')
    else:
        form = LoginForm()

    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    return redirect('login')



@login_required
@requiere_postulante
def datos_personales(request):
    postulante = request.user.postulante

    if request.method == 'POST':
        form = DatosPersonalesForm(request.POST, instance=postulante)
        if form.is_valid():
            service.actualizar_datos_postulante(request.user, form)
            return redirect('datos_personales_exitoso')
    else:
        form = DatosPersonalesForm(instance=postulante, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })

    return render(request, 'usuarios/datos_personales.html', {'form': form})


def datos_personales_exitoso(request):
    return render(request, 'usuarios/exito.html', {
        'titulo': '¡Datos guardados!',
        'mensaje': 'Tu información personal fue actualizada correctamente.',
        'link_url': reverse('datos_personales'),
        'link_texto': 'Volver a mis datos',
    })
