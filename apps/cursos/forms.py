from django import forms
from .models import Curso, Categoria

INPUT_CLASS = "w-full px-4 py-2 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-primary/30"

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nombre', 'categoria', 'imagen', 'descripcion', 'duracion', 'horario', 'tipo', 'url_externa']
        labels = {
            'nombre': 'Nombre',
            'categoria': 'Categoria',
            'imagen': 'Imagen',
            'descripcion': 'Descripcion',
            'duracion': 'Duracion',
            'horario': 'Horario',
            'tipo': 'Tipo',
            'url_externa': 'URL externa',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. Python desde cero'}),
            'categoria': forms.Select(attrs={'class': INPUT_CLASS}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'hidden', 'id': 'imagen-input'}),
            'descripcion': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 4, 'placeholder': 'Descripcion del curso'}),
            'duracion': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. 6 meses'}),
            'horario': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. Lunes y Miercoles 18:00 - 21:00'}),
            'tipo': forms.Select(attrs={'class': INPUT_CLASS}),
            'url_externa': forms.URLInput(attrs={'class': INPUT_CLASS, 'placeholder': 'https://ien.edu.ar/cursos/...'}),
        }

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre']
        labels = {
            'nombre': 'Nombre',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. Programacion'}),
        }