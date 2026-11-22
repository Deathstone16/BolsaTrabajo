"""Formularios y validaciones para ofertas y habilidades laborales."""

from ientrabajo.form_fields import DescripcionField
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from uuid import NAMESPACE_URL, uuid5
import json
import re
from .models import Oferta
from categorias.models import Categoria, Habilidad

INPUT_CLASS = "w-full px-4 py-2 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-primary/30"


class OfertaForm(forms.ModelForm):
    """Valida y persiste los datos utilizados para crear o editar una oferta."""
    descripcion = DescripcionField()

    categoria = forms.ModelChoiceField(
        label='Categoría',
        queryset=Categoria.objects.all(),
        required=True,
        empty_label="Seleccionar categoría",
    )
    requisitos_obligatorios = forms.CharField(
        label='Requisitos obligatorios', required=True,
        help_text='Condiciones indispensables para el puesto. Separá los elementos con Enter, coma o punto y coma.',
        widget=forms.Textarea(attrs={'rows': 5}),
    )
    requisitos_deseables = forms.CharField(
        label='Requisitos deseables', required=False,
        help_text='Conocimientos que suman valor, pero no son indispensables. Separalos con Enter, coma o punto y coma.',
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
            sections = {
                'mandatory': (self.instance.requisitos_obligatorios or '').splitlines(),
                'desirable': (self.instance.requisitos_deseables or '').splitlines(),
            }
            category_by_name = {}
            for item in self.instance.requisitos_estructurados or []:
                if item.get('source') in ('requisitos_obligatorios', 'requisitos_deseables'):
                    category_by_name[item.get('name', '').casefold()] = item.get('skill_category', item.get('category', 'technical_skills'))
            seen = {text.strip().casefold() for lines in sections.values() for text in lines if text.strip()}
            for field, category in (('habilidades_duras', 'technical_skills'), ('habilidades_blandas', 'soft_skills')):
                for text in (getattr(self.instance, field) or '').split(','):
                    text = text.strip()
                    if not text:
                        continue
                    if category_by_name.get(text.casefold()) not in self.CATEGORIAS_REQUISITO:
                        category_by_name[text.casefold()] = category
                    if text.casefold() not in seen:
                        sections['desirable'].append(text)
                        seen.add(text.casefold())
            if self.instance.requiere_revision_requisitos:
                for text in (self.instance.habilidades_requeridas or '').split(','):
                    text = text.strip()
                    if text and text.casefold() not in seen:
                        sections['desirable'].append(text)
                        seen.add(text.casefold())
            categories = {}
            for key, field in (('mandatory', 'requisitos_obligatorios'), ('desirable', 'requisitos_deseables')):
                lines = [text.strip() for text in sections[key] if text.strip()]
                self.initial[field] = '\n'.join(lines)
                categories[key] = [category_by_name.get(text.casefold(), 'technical_skills') for text in lines]
                categories[key] = [value if value in self.CATEGORIAS_REQUISITO else 'technical_skills' for value in categories[key]]
            self.initial['categorias_requisitos'] = json.dumps(categories)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.HiddenInput, forms.CheckboxInput)):
                field.widget.attrs['class'] = 'input-ien'
        for name in ('experiencia_clasificacion', 'educacion_clasificacion'):
            self.fields[name].label = '¿Es indispensable o deseable?'
        self.fields['nivel_educativo'].required = False
        self.fields['ubicacion'].widget.attrs.update({'id': 'input-ubicacion', 'autocomplete': 'off'})
        for field in ('requisitos_obligatorios', 'requisitos_deseables'):
            self.fields[field].widget.attrs.update({'class': 'input-ien', 'maxlength': 10000})

    class Meta:
        model = Oferta
        fields = [
            "titulo",
            "nombre_puesto",
            "categoria",
            "ubicacion",
            "modalidad",
            "descripcion",
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

        labels = {
            'titulo': 'Título de la oferta', 'nombre_puesto': 'Nombre del puesto',
            'ubicacion': 'Ubicación', 'categoria': 'Categoría',
            'descripcion': 'Descripción del puesto', 'fecha_cierre': 'Fecha de cierre',
            'experiencia_requerida': 'Experiencia', 'nivel_educativo': 'Nivel educativo',
        }
        widgets = {
            "fecha_cierre": forms.DateInput(format='%Y-%m-%d', attrs={"type": "date"}),
            "experiencia_clasificacion": forms.Select(attrs={'class': INPUT_CLASS}),
            "educacion_clasificacion": forms.Select(attrs={'class': INPUT_CLASS}),
        }

    def _normalizar_requisitos(self, campo):
        values = [re.sub(r'\s+', ' ', value).strip() for value in re.split(r'[,;\r\n]+', self.cleaned_data.get(campo, ''))]
        values = [value for value in values if value]
        if campo == 'requisitos_obligatorios' and not values:
            raise forms.ValidationError('Agregá al menos un requisito obligatorio.')
        if len(values) > 30:
            raise forms.ValidationError('Podés agregar hasta 30 requisitos por lista.')
        if any(len(value) < 2 or len(value) > 100 for value in values):
            raise forms.ValidationError('Cada requisito debe tener entre 2 y 100 caracteres.')
        if len(values) != len({value.casefold() for value in values}):
            raise forms.ValidationError('Hay requisitos repetidos. Dejá cada uno una sola vez.')
        return '\n'.join(values)

    def clean_requisitos_obligatorios(self):
        return self._normalizar_requisitos('requisitos_obligatorios')

    def clean_requisitos_deseables(self):
        return self._normalizar_requisitos('requisitos_deseables')

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
        result = {}
        for key, field in (('mandatory', 'requisitos_obligatorios'), ('desirable', 'requisitos_deseables')):
            lines = self.cleaned_data.get(field, '').splitlines()
            categories = mapping.get(key, ['technical_skills'] * len(lines) if key == 'desirable' else [])
            if not isinstance(categories, list) or len(categories) != len(lines) or any(not isinstance(item, str) or item not in self.CATEGORIAS_REQUISITO for item in categories):
                raise forms.ValidationError('Elegí un tipo válido para cada requisito de las dos listas.')
            result[key] = categories
        return result

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('educacion_clasificacion') != 'no_solicitado' and not cleaned.get('nivel_educativo'):
            self.add_error('nivel_educativo', 'Elegí el nivel educativo o marcá la formación como no solicitada.')
        mandatory_set = {value.casefold() for value in cleaned.get('requisitos_obligatorios', '').splitlines()}
        if any(value.casefold() in mandatory_set for value in cleaned.get('requisitos_deseables', '').splitlines()):
            self.add_error('requisitos_deseables', 'Un requisito no puede ser obligatorio y deseable a la vez. Dejalo en una sola lista.')
        description = (cleaned.get('descripcion') or '').casefold()
        mandatory_text = '\n'.join((cleaned.get('requisitos_obligatorios') or '').splitlines()).casefold()
        if any(word in description for word in ('excluyente', 'obligatorio', 'indispensable', 'requisito mínimo')) and not any(word in mandatory_text for word in ('excluyente', 'obligatorio', 'indispensable', 'requisito mínimo')):
            self.warnings.append('La descripción parece mencionar una condición excluyente. Revisá que esté clasificada en Requisitos obligatorios.')
        return cleaned

    def save(self, commit=True):
        """Mantiene el campo heredado a partir de las dos secciones nuevas."""
        oferta = super().save(commit=False)
        mapping = self.cleaned_data['categorias_requisitos']
        skills = {'technical_skills': [], 'soft_skills': []}
        for key, field in (('mandatory', 'requisitos_obligatorios'), ('desirable', 'requisitos_deseables')):
            for text, category in zip(self.cleaned_data.get(field, '').splitlines(), mapping[key]):
                if category in skills:
                    skills[category].append(text)
        oferta.habilidades_duras = ', '.join(skills['technical_skills'])
        oferta.habilidades_blandas = ', '.join(skills['soft_skills'])
        oferta.habilidades_requeridas = ', '.join(filter(None, [oferta.habilidades_duras, oferta.habilidades_blandas]))
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
                    **({'skill_category': mapping['desirable'][index]} if not mandatory else {}),
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
        oferta.requisitos_estructurados = structured
        oferta.requiere_revision_requisitos = False
        if commit:
            oferta.save()
        return oferta

class HabilidadForm(forms.ModelForm):
    """Formulario administrativo para crear o modificar una habilidad."""
    tipo_habilidad = forms.ChoiceField(
        label='Tipo de habilidad',
        choices=[('D', 'Habilidad técnica'), ('B', 'Habilidad blanda')],
        widget=forms.Select(attrs={'class': 'input-ien'}),
    )
    class Meta:
        model = Habilidad
        fields = ["nombre", "tipo_habilidad"]
        labels = {"nombre": "Nombre de la habilidad", "tipo_habilidad": "Tipo de habilidad"}
        widgets = {
            "nombre": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "Ej. Python"}
            ),
            "tipo_habilidad": forms.Select(attrs={"class": 'input-ien'}),
        }

    def clean_nombre(self):
        """Valida la longitud mínima del nombre de la habilidad."""
        nombre = self.cleaned_data.get("nombre")
        if nombre and len(nombre) < 2:
            raise forms.ValidationError("El nombre debe tener al menos 2 caracteres.")
        if nombre:
            duplicadas = Habilidad.objects.filter(categoria_id=self.instance.categoria_id, nombre__iexact=nombre)
            if self.instance.pk:
                duplicadas = duplicadas.exclude(pk=self.instance.pk)
            if duplicadas.exists():
                raise forms.ValidationError('Ya existe una habilidad con ese nombre en esta categoría.')
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



