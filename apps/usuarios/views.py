from .decorators import postulante_required
from django.shortcuts import redirect, render
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import RegistroPostulanteForm, RegistroOferenteForm, LoginForm, DatosPersonalesForm, OferenteForm
from .decorators import postulante_required, oferente_required
from .models import Oferente


from .forms import RegistroPostulanteForm, RegistroOferenteForm, LoginForm, DatosPersonalesForm, OferenteForm
from . import service


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
                
                if hasattr(request.user, 'oferente'):
                    return redirect('dashboard_empresa')
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
@oferente_required
def editar_perfil_empresa(request):
    oferente = request.user.oferente

    if request.method == 'POST':
        form = OferenteForm(request.POST, request.FILES, instance=oferente)
        if form.is_valid():
            form.save()
            return redirect('dashboard_empresa')
    else:
        form = OferenteForm(instance=oferente)

    return render(request, 'ofertas/editar-perfil.html', {'form': form, 'oferente': oferente})


@login_required
@postulante_required
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

@login_required
@postulante_required
def perfil_oferente(request, pk):
    oferente = get_object_or_404(Oferente, pk=pk)
    ofertas = oferente.usuario.ofertas.filter(estado='activa')
    return render(request, 'Ofertas/perfil_oferente_publico.html', {
        'oferente': oferente,
        'ofertas': ofertas,
    })

def datos_personales_exitoso(request):
    return render(request, 'usuarios/exito.html', {
        'titulo': '¡Datos guardados!',
        'mensaje': 'Tu información personal fue actualizada correctamente.',
        'link_url': reverse('datos_personales'),
        'link_texto': 'Volver a mis datos',
    })


@login_required
@postulante_required
def mi_perfil(request):
    postulante = request.user.postulante
    return render(request, 'usuarios/mi_perfil.html', {'postulante': postulante})
