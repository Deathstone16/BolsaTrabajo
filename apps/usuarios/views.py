from django.shortcuts import redirect, render
from django.contrib.auth import login, authenticate, logout
from .forms import RegistroPostulanteForm, RegistroOferenteForm, LoginForm, DatosPersonalesForm,OferenteForm
from django.contrib.auth.decorators import login_required

def registro(request):
    tipo = request.GET.get('tipo', 'postulante')
    
    if tipo == 'oferente':
        FormClass = RegistroOferenteForm
    else:
        FormClass = RegistroPostulanteForm

    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('registro_exitoso')
    else:
        form = FormClass()

    return render(request, 'usuarios/registro.html', {'form': form, 'tipo': tipo})

def registro_exitoso(request):
    return render(request, 'usuarios/registro_exitoso.html')

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, email=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                form.add_error(None, 'Email o contraseña incorrectos.')
    else:
        form = LoginForm()

    return render(request, 'usuarios/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def datos_personales(request):
    postulante = request.user.postulante
    
    if request.method == 'POST':
        form = DatosPersonalesForm(request.POST, instance=postulante)
        if form.is_valid():
            postulante = form.save(commit=False)
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.email = form.cleaned_data['email']
            request.user.save()
            postulante.save()
            return redirect('datos_personales_exitoso')
    else:
        form = DatosPersonalesForm(instance=postulante, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })

    return render(request, 'usuarios/datos_personales.html', {'form': form})

def datos_personales_exitoso(request):
    return render(request, 'usuarios/datos_personales_exitoso.html')
