from django.shortcuts import render


def home(request):
    featured_jobs = [
        {
            "id": 1,
            "title": "Desarrollador Full Stack",
            "company": "TechSolutions SA",
            "location": "CABA",
            "modality": "Remoto"
        },
        {
            "id": 2,
            "title": "Analista de Datos",
            "company": "DataMetrics",
            "location": "CABA",
            "modality": "Híbrido"
        },
        {
            "id": 3,
            "title": "Diseñador UX/UI",
            "company": "CreativeLab",
            "location": "La Plata",
            "modality": "Presencial"
        },
    ]
    return render(request, 'base.html', {'featured_jobs': featured_jobs})