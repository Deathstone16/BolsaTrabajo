from django.shortcuts import redirect, render
from django.contrib.auth import login, authenticate
from .forms import RegistroForm, LoginForm
from django.contrib.auth import logout

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect('/')
    
    else:
        form = RegistroForm()
    
    return render(request, 'usuarios/registro.html', {'form': form})




def login_view(request):
    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request,user)
                return redirect('/')
            else:
                form.add_error(None,'Email o contraseña incorrectos')
    return render(request,'usuarios/login.html',{'form': form})
# Create your views here.

def logout_view(request):
    logout(request)
    return redirect('/')