"""Formularios y validaciones para ofertas y habilidades laborales."""

from ientrabajo.form_fields import DescripcionField
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from uuid import NAMESPACE_URL, uuid5
import json
from .models import Oferta
from categorias.models import Categoria, Habilidad

INPUT_CLASS = "w-full px-4 py-2 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-primary/30"


class OfertaForm(forms.ModelForm):
    """Valida y persiste los datos utilizados para crear o editar una oferta."""
    descripcion = DescripcionField()

    MAX_POR_SECCION = 10
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        required=True,
        empty_label="Seleccionar categoría",
    )
    requisitos_obligatorios = forms.CharField(
        label='Requisitos obligatorios', required=True,
        help_text='TODO requisito en este campo se considerará obligatorio. Separá cada requisito con un salto de línea. Lo que no sea indispensable va en Requisitos deseables.',
        widget=forms.Textarea(attrs={'rows': 5}),
    )
    requisitos_deseables = forms.CharField(
        label='Requisitos deseables', required=False,
        help_text='Incluí conocimientos o experiencia que suman valor, pero cuya ausencia no implica incumplir un requisito obligatorio.',
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    categorias_requisitos = forms.CharField(required=False, widget=forms.HiddenInput())
    CATEGORIAS_REQUISITO = {
        'technical_skills', 'soft_skills', 'experience', 'education', 'languages', 'logistics',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.warnings = []
        if self.instance and self.instance.pk and not self.is_bound:
            if self.instance.requiere_revision_requisitos and not self.instance.requisitos_deseables:
                legacy = [item.strip() for item in (self.instance.habilidades_requeridas or '').split(',') if item.strip()]
                self.initial['requisitos_deseables'] = '\n'.join(legacy)
            categories = {}
            for item in self.instance.requisitos_estructurados or []:
                if item.get('source') == 'requisitos_obligatorios':
                    categories.setdefault('mandatory', []).append(item.get('category', 'technical_skills'))
            self.initial['categorias_requisitos'] = json.dumps({'mandatory': categories.get('mandatory', [])})
        for field in ('requisitos_obligatorios', 'requisitos_deseables'):
            self.fields[field].widget.attrs.update({'class': INPUT_CLASS + ' w-full', 'maxlength': 10000})

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
            "requisitos_obligatorios",
            "requisitos_deseables",
            "categorias_requisitos",
            "experiencia_requerida",
            "nivel_educativo",
            "experiencia_clasificacion",
            "educacion_clasificacion",
            "es_confidencial",
            "fecha_cierre",
        ]

        widgets = {
            "fecha_cierre": forms.DateInput(attrs={"type": "date"}),
            "habilidades_duras": forms.HiddenInput(),
            "habilidades_blandas": forms.HiddenInput(),
            "experiencia_clasificacion": forms.Select(attrs={'class': INPUT_CLASS}),
            "educacion_clasificacion": forms.Select(attrs={'class': INPUT_CLASS}),
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

    def clean_categorias_requisitos(self):
        raw = self.cleaned_data.get('categorias_requisitos') or '{}'
        try:
            mapping = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            raise forms.ValidationError('Revisá la categoría de cada requisito obligatorio.')
        if not isinstance(mapping, dict):
            raise forms.ValidationError('La clasificación de requisitos no es válida.')
        mandatory = [line.strip() for line in self.cleaned_data.get('requisitos_obligatorios', '').splitlines() if line.strip()]
        categories = mapping.get('mandatory', [])
        if not isinstance(categories, list) or len(categories) != len(mandatory) or any(item not in self.CATEGORIAS_REQUISITO for item in categories):
            raise forms.ValidationError('Elegí una categoría válida para cada requisito obligatorio.')
        for line in mandatory + [line.strip() for line in self.cleaned_data.get('requisitos_deseables', '').splitlines() if line.strip()]:
            if len(line) > 100:
                raise forms.ValidationError('Cada requisito puede tener hasta 100 caracteres. Separá requisitos largos en varias líneas.')
        return {'mandatory': categories}

    def clean(self):
        cleaned = super().clean()
        description = (cleaned.get('descripcion') or '').casefold()
        mandatory_text = '\n'.join((cleaned.get('requisitos_obligatorios') or '').splitlines()).casefold()
        if any(word in description for word in ('excluyente', 'obligatorio', 'indispensable', 'requisito mínimo')) and not any(word in mandatory_text for word in ('excluyente', 'obligatorio', 'indispensable', 'requisito mínimo')):
            self.warnings.append('La descripción parece mencionar una condición excluyente. Revisá que esté clasificada en Requisitos obligatorios.')
        return cleaned

    def save(self, commit=True):
        """Mantiene el campo heredado a partir de las dos secciones nuevas."""
        oferta = super().save(commit=False)
        oferta.habilidades_requeridas = ", ".join(
            filter(None, [oferta.habilidades_duras, oferta.habilidades_blandas])
        )
        structured = []
        mapping = self.cleaned_data.get('categorias_requisitos', {})
        seen = set()
        for field_name, default_category, mandatory in (
            ('requisitos_obligatorios', None, True),
            ('requisitos_deseables', 'desirables', False),
        ):
            lines = [line.strip() for line in getattr(oferta, field_name).splitlines() if line.strip()]
            for index, text in enumerate(lines):
                if not text or text.casefold() in seen:
                    continue
                seen.add(text.casefold())
                category = mapping['mandatory'][index] if mandatory else default_category
                structured.append({
                    'id': str(uuid5(NAMESPACE_URL, f'ien-offer:{field_name}:{category}:{text.casefold()}')),
                    'category': category,
                    'source': field_name,
                    'name': text[:100],
                    'mandatory': mandatory,
                    'exclusionary': mandatory and any(word in text.casefold() for word in ('excluyente', 'indispensable', 'obligatorio')),
                })
        for field_name, category, value_field in (
            ('experiencia_clasificacion', 'experience', 'experiencia_requerida'),
            ('educacion_clasificacion', 'education', 'nivel_educativo'),
        ):
            classification = getattr(oferta, field_name)
            value = getattr(oferta, value_field)
            if classification != 'no_solicitado' and value:
                years = {
                    'sin-experiencia': 0, 'menos-1': 0, '1-2': 1, '2-3': 2,
                    '3-5': 3, '5+': 5,
                }
                is_desirable = classification == 'deseable'
                requirement_category = 'desirables' if is_desirable else category
                display_value = (
                    oferta.get_experiencia_requerida_display()
                    if value_field == 'experiencia_requerida'
                    else oferta.get_nivel_educativo_display()
                )
                structured.append({
                    'id': str(uuid5(NAMESPACE_URL, f'ien-offer:{requirement_category}:{value_field}:{value}:{classification}')),
                    'category': requirement_category,
                    'source': value_field,
                    'name': display_value,
                    'mandatory': classification == 'obligatorio',
                    'exclusionary': False,
                    **({'minimum_years': years[value]} if value_field == 'experiencia_requerida' else {}),
                })
        # Los tags estructurados fuera del textarea obligatorio se clasifican como deseables.
        for field_name, category in (('habilidades_duras', 'technical_skills'), ('habilidades_blandas', 'soft_skills')):
            for text in (getattr(oferta, field_name) or '').split(','):
                text = text.strip()
                if text and text.casefold() not in seen:
                    seen.add(text.casefold())
                    structured.append({
                        'id': str(uuid5(NAMESPACE_URL, f'ien-offer:desirables:{field_name}:{text.casefold()}')),
                        'category': 'desirables', 'source': field_name, 'name': text,
                        'mandatory': False, 'exclusionary': False,
                    })
        oferta.requisitos_estructurados = structured
        oferta.requiere_revision_requisitos = False
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



