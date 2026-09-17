from django.contrib import messages
from django.shortcuts import redirect, render
def home(request):
    featured_jobs = [
        {"id": 1, "title": "Desarrollador Full Stack", "company": "TechSolutions SA", "location": "CABA", "modality": "Remoto"},
        {"id": 2, "title": "Analista de Datos", "company": "DataMetrics", "location": "CABA", "modality": "Híbrido"},
        {"id": 3, "title": "Diseñador UX/UI", "company": "CreativeLab", "location": "La Plata", "modality": "Presencial"},
    ]
    return render(request, 'home.html', {'featured_jobs': featured_jobs})

def ia(request):
    """Ruta temporal: evita ejecutar Groq dentro de Django."""
    messages.info(request, "El análisis de CV se solicita desde Mi perfil.")
    return redirect('home')
