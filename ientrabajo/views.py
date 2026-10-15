"""Vistas generales que no pertenecen a una aplicación específica."""

from django.contrib import messages
from django.shortcuts import redirect, render

from cursos.models import Curso
from ofertas.models import Oferta
from usuarios.models import Oferente


def _contexto_home():
    """Datos de la portada: ofertas reales y contadores de la base."""
    ofertas_activas = Oferta.objects.filter(estado='activa').select_related('empresa__oferente')
    destacadas = list(ofertas_activas[:6])
    cursos = Curso.objects.filter(activo=True).select_related('categoria').order_by('nombre')

    return {
        'vista_activa': 'inicio',
        'ofertas_destacadas': destacadas,
        'cursos': cursos,
        'modalidad_choices': Oferta.MODALIDAD_CHOICES,
        'experiencia_choices': Oferta.EXPERIENCIA_CHOICES,
        'total_ofertas': ofertas_activas.count(),
        'total_empresas': Oferente.objects.aprobados().count(),
        'total_cursos': cursos.count(),
    }


def home(request):
    """Renderiza la portada con cursos y ofertas destacadas."""
    return render(request, 'nueva_ui/home.html', _contexto_home())

def ia(request):
    """Ruta temporal: evita ejecutar Groq dentro de Django."""
    messages.info(request, "El análisis de CV se solicita desde Mi perfil.")
    return redirect('home')
