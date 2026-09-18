from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Oferta
from categorias.models import Categoria, Habilidad

INPUT_CLASS = "w-full px-4 py-2 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-primary/30"


class OfertaForm(forms.ModelForm):
    MAX_POR_SECCION = 10  
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        required=True,
        empty_label="Seleccionar categoría",
    )

    class Meta:
        model = Oferta
        fields = [
            "titulo",
            "nombre_puesto",
            "categoria",
            "ubicacion",
            "modalidad",
            "descripcion",
            "habilidades_duras",     
            "habilidades_blandas",
            "habilidades_requeridas",
            "experiencia_requerida",
            "nivel_educativo",
            "es_confidencial",
            "fecha_cierre",
        ]

        widgets = {
            "fecha_cierre": forms.DateInput(attrs={"type": "date"}),
            "habilidades_duras": forms.HiddenInput(),      
            "habilidades_blandas": forms.HiddenInput(),
            "habilidades_requeridas": forms.HiddenInput(),
        }

    def _validar_tags(self, value, es_duras=False):
        """Valida string 'tag1, tag2, tag3' y retorna lista limpia para cross-validation."""
        tags = [t.strip() for t in value.split(",") if t.strip()]
        for t in tags:
            if len(t) < 2 or len(t) > 60:
                raise forms.ValidationError(f"'{t}' debe tener entre 2 y 60 caracteres.")
        if len(tags) != len(set(tags)):
            raise forms.ValidationError("Hay habilidades repetidas en esta sección.")
        if len(tags) > self.MAX_POR_SECCION:
            raise forms.ValidationError(f"Máximo {self.MAX_POR_SECCION} habilidades por sección.")
        if es_duras and len(tags) < 1:
            raise forms.ValidationError("Agregá al menos 1 habilidad técnica.")
        return tags

def clean_habilidades_duras(self):
    value = self.cleaned_data.get("habilidades_duras", "")
    self._validar_tags(value, es_duras=True)
    return value

def clean_habilidades_blandas(self):
    value = self.cleaned_data.get("habilidades_blandas", "")
    tags_blandas = self._validar_tags(value)
    # Cross-validation con duras
    duras_value = self.cleaned_data.get("habilidades_duras", "")
    tags_duras = [t.strip().lower() for t in duras_value.split(",") if t.strip()]
    duplicadas = set(t.lower() for t in tags_blandas) & set (tags_duras)
    if duplicadas:
        raise forms.ValidationError(
            "Estas habilidades ya están en la sección técnica: " + ", ".join(sorted(duplicadas))
        )
    return value

def clean_titulo(self):
    titulo = self.cleaned_data.get("titulo")
    if titulo and (len(titulo) < 5 or len(titulo) > 100):
        raise forms.ValidationError("El título debe tener entre 5 y 100 caracteres.")
    return titulo

def clean_fecha_cierre(self):
    fecha_cierre = self.cleaned_data.get("fecha_cierre")
    if fecha_cierre and fecha_cierre <= timezone.now():
        raise forms.ValidationError("La fecha de cierre debe ser posterior a la fecha actual del sistema.")
    return fecha_cierre



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

    def validate_unique(self):
        """Valida la unicidad (nombre, categoria) como error de formulario.

        Django excluye de la validacion de unicidad los campos que no estan
        en el form. Como `categoria` la asigna la URL y no el usuario,
        quedaria fuera y la restriccion recien saltaria en la base como
        IntegrityError. La sacamos de las exclusiones para que el duplicado
        se muestre como error de campo.
        """
        exclude = self._get_validation_exclusions()
        exclude.discard("categoria")
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            self._update_errors(e)




