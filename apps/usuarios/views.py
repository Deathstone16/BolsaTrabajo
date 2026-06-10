from django.shortcuts import redirect, render
from django.contrib.auth import login, authenticate, logout
from .forms import RegistroPostulanteForm, RegistroOferenteForm, LoginForm, OferenteForm
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
            user = authenticate(request, username=email, password=password)
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
def editar_perfil_empresa(request):
    if not hasattr(request.user, 'oferente'):
        return redirect('home')
    
    oferente = request.user.oferente
    
    if request.method == 'POST':
        form = OferenteForm(request.POST, request.FILES, instance=oferente)
        if form.is_valid():
            form.save()
            return redirect('dashboard_empresa')
    else:
        form = OferenteForm(instance=oferente)
    
    return render(request, 'ofertas/editar-perfil.html', {'form': form, 'oferente': oferente})