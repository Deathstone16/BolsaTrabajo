from django.shortcuts import render
from ia.services import call
def home(request):
    featured_jobs = [
        {"id": 1, "title": "Desarrollador Full Stack", "company": "TechSolutions SA", "location": "CABA", "modality": "Remoto"},
        {"id": 2, "title": "Analista de Datos", "company": "DataMetrics", "location": "CABA", "modality": "Híbrido"},
        {"id": 3, "title": "Diseñador UX/UI", "company": "CreativeLab", "location": "La Plata", "modality": "Presencial"},
    ]
    return render(request, 'home.html', {'featured_jobs': featured_jobs})

def ia(request):
    call()
    featured_jobs = [
        {"id": 1, "title": "Desarrollador Full Stack", "company": "TechSolutions SA", "location": "CABA", "modality": "Remoto"},
        {"id": 2, "title": "Analista de Datos", "company": "DataMetrics", "location": "CABA", "modality": "Híbrido"},
        {"id": 3, "title": "Diseñador UX/UI", "company": "CreativeLab", "location": "La Plata", "modality": "Presencial"},
    ]
    return render(request, 'home.html', {'featured_jobs': featured_jobs})