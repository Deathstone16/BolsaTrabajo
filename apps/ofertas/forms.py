from django import forms
from django.utils import timezone
from .models import Oferta

class OfertaForm(forms.ModelForm):
    class Meta:
        model = Oferta
        fields = [
            'titulo', 'nombre_puesto', 'categoria', 'ubicacion', 'modalidad', 
            'descripcion', 'requisitos', 'habilidades_requeridas', 
            'experiencia_requerida', 'nivel_educativo', 'es_confidencial', 'fecha_cierre'
        ]
        
        widgets = {
            'fecha_cierre': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_titulo(self):
        titulo = self.cleaned_data.get('titulo')
        if titulo and (len(titulo) < 5 or len(titulo) > 100):
            raise forms.ValidationError("El título debe tener entre 5 y 100 caracteres.")
        return titulo

    def clean_fecha_cierre(self):
        fecha_cierre = self.cleaned_data.get('fecha_cierre')
        if fecha_cierre and fecha_cierre <= timezone.now():
            raise forms.ValidationError("La fecha de cierre debe ser posterior a la fecha actual del sistema.")
        return fecha_cierre