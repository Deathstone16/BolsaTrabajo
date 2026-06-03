from django.shortcuts import redirect, render
from django.contrib.auth import login
from .forms import RegistroForm

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

# Create your views here.
