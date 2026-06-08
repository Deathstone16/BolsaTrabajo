from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import OfertaForm
from .services import crear_oferta_laboral

@login_required
def crear_oferta(request):
    es_oferente = hasattr(request.user, 'oferente')
    if not es_oferente:
        return redirect('home')

    if request.method == 'POST':
        form = OfertaForm(request.POST)
        if form.is_valid():
            crear_oferta_laboral(request.user, form)
            return redirect('home')
    else:
        form = OfertaForm()

    return render(request, 'Ofertas/publicar-empleo.html', {'form': form})