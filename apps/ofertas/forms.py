"""Formularios y validaciones para ofertas y habilidades laborales."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Oferta
from categorias.models import Categoria, Habilidad

INPUT_CLASS = "w-full px-4 py-2 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-primary/30"


class OfertaForm(forms.ModelForm):
    """Valida y persiste los datos utilizados para crear o editar una oferta."""

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
            "experiencia_requerida",
            "nivel_educativo",
            "es_confidencial",
            "fecha_cierre",
        ]

        widgets = {
            "fecha_cierre": forms.DateInput(attrs={"type": "date"}),
            "habilidades_duras": forms.HiddenInput(),
            "habilidades_blandas": forms.HiddenInput(),
        }

    def _validar_tags(self, value, es_duras=False):
        """Valida las habilidades de una sección y devuelve sus nombres."""
        tags = [t.strip() for t in value.split(",") if t.strip()]
        for t in tags:
            if len(t) < 2 or len(t) > 60:
                raise forms.ValidationError(f"'{t}' debe tener entre 2 y 60 caracteres.")
        if len(tags) != len({tag.casefold() for tag in tags}):
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
        duras_value = self.cleaned_data.get("habilidades_duras", "")
        tags_duras = {t.strip().casefold() for t in duras_value.split(",") if t.strip()}
        duplicadas = {t.casefold() for t in tags_blandas} & tags_duras
        if duplicadas:
            raise forms.ValidationError(
                "Estas habilidades ya están en la sección técnica: "
                + ", ".join(sorted(duplicadas))
            )
        return value

    def clean_titulo(self):
        """Comprueba que el título tenga una longitud útil para publicación."""
        titulo = self.cleaned_data.get("titulo")
        if titulo and (len(titulo) < 5 or len(titulo) > 100):
            raise forms.ValidationError(
                "El título debe tener entre 5 y 100 caracteres."
            )
        return titulo

    def clean_fecha_cierre(self):
        """Impide publicar una oferta cuya fecha de cierre ya haya pasado."""
        fecha_cierre = self.cleaned_data.get("fecha_cierre")
        if fecha_cierre and fecha_cierre <= timezone.now():
            raise forms.ValidationError(
                "La fecha de cierre debe ser posterior a la fecha actual del sistema."
            )
        return fecha_cierre

    def save(self, commit=True):
        """Mantiene el campo heredado a partir de las dos secciones nuevas."""
        oferta = super().save(commit=False)
        oferta.habilidades_requeridas = ", ".join(
            filter(None, [oferta.habilidades_duras, oferta.habilidades_blandas])
        )
        if commit:
            oferta.save()
        return oferta

class HabilidadForm(forms.ModelForm):
    """Formulario administrativo para crear o modificar una habilidad."""
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
        """Valida la longitud mínima del nombre de la habilidad."""
        nombre = self.cleaned_data.get("nombre")
        if nombre and len(nombre) < 2:
            raise forms.ValidationError("El nombre debe tener al menos 2 caracteres.")
        return nombre

    def validate_unique(self):
        """Valida la unicidad (nombre, tipo_oferta) como error de formulario.

        Django excluye de la validacion de unicidad los campos que no estan
        en el form. Como `tipo_oferta` lo asigna la URL y no el usuario,
        quedaria fuera y la restriccion recien saltaria en la base como
        IntegrityError. Lo sacamos de las exclusiones para que el duplicado
        se muestre como error de campo.
        """
        exclude = self._get_validation_exclusions()
        exclude.discard("categoria")  
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            self._update_errors(e)



