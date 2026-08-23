from django import forms
from django.utils import timezone
from .models import Oferta
from categorias.models import Categoria, Habilidad

INPUT_CLASS = "w-full px-4 py-2 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-primary/30"


class OfertaForm(forms.ModelForm):
    tipo_oferta = forms.ModelChoiceField(
        queryset=Categoria.objects.none(),
        required=False,
        empty_label="Seleccionar tipo de oferta",
    )
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        required=False,
        empty_label="Seleccionar categoría",
    )

    class Meta:
        model = Oferta
        fields = [
            "titulo",
            "nombre_puesto",
            "tipo_oferta",
            "categoria",
            "ubicacion",
            "modalidad",
            "descripcion",
            "habilidades_requeridas",
            "experiencia_requerida",
            "nivel_educativo",
            "es_confidencial",
            "fecha_cierre",
        ]

        widgets = {
            "fecha_cierre": forms.DateInput(attrs={"type": "date"}),
            "habilidades_requeridas": forms.HiddenInput(),
        }

    def clean_titulo(self):
        titulo = self.cleaned_data.get("titulo")
        if titulo and (len(titulo) < 5 or len(titulo) > 100):
            raise forms.ValidationError(
                "El título debe tener entre 5 y 100 caracteres."
            )
        return titulo

    def clean_fecha_cierre(self):
        fecha_cierre = self.cleaned_data.get("fecha_cierre")
        if fecha_cierre and fecha_cierre <= timezone.now():
            raise forms.ValidationError(
                "La fecha de cierre debe ser posterior a la fecha actual del sistema."
            )
        return fecha_cierre

    def clean_experiencia_requerida(self):
        valor = self.cleaned_data.get("experiencia_requerida")
        if valor is not None and valor < 0:
            raise forms.ValidationError(
                "Los años de experiencia no pueden ser negativos."
            )
        return valor



class HabilidadForm(forms.ModelForm):
    class Meta:
        model = Habilidad
        fields = ["nombre"]
        labels = {"nombre": "Nombre"}
        widgets = {
            "nombre": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Ej. Python"}
            ),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre")
        if nombre and len(nombre) < 2:
            raise forms.ValidationError("El nombre debe tener al menos 2 caracteres.")
        return nombre

