"""Formularios administrativos para cursos y categorías."""

import re

from ientrabajo.form_fields import DescripcionField

from django import forms
from .models import Curso, Categoria
from .covers import COVER_RULES, COVER_THEMES, course_cover_theme, cached_category_name

INPUT_CLASS = "w-full px-4 py-2 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-primary/30"


class CursoFiltroForm(forms.Form):
    """Filtros públicos con opciones tomadas del catálogo activo."""

    q = forms.CharField(
        label='Buscar por título', required=False, max_length=120,
        widget=forms.TextInput(attrs={'type': 'search', 'placeholder': 'Ej. Excel, administración…'}),
    )
    categoria = forms.ModelChoiceField(
        label='Categoría', required=False, queryset=Categoria.objects.none(),
        empty_label='Todas las categorías',
    )
    modalidad = forms.ChoiceField(
        label='Modalidad', required=False,
        choices=[('', 'Todas'), *Curso.TIPO_CHOICES],
    )
    duracion = forms.ChoiceField(label='Duración', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        activos = Curso.objects.filter(activo=True)
        self.fields['categoria'].queryset = Categoria.objects.filter(
            pk__in=activos.values('categoria_id'),
        ).order_by('nombre')
        duraciones = activos.exclude(duracion='').order_by('duracion').values_list(
            'duracion', flat=True,
        ).distinct()
        self.fields['duracion'].choices = [('', 'Todas las duraciones')] + [
            (duracion, duracion) for duracion in duraciones
        ]
        for field in self.fields.values():
            field.widget.attrs['class'] = 'input-ien'


class CourseImageInput(forms.ClearableFileInput):
    template_name = 'cursos/widgets/course_image.html'
    cover_theme = 'comunicacion'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['cover_path'] = f'images/cursos/{self.cover_theme}-predeterminada.webp'
        context['widget']['cover_choices'] = [
            {'theme': theme, 'path': f'images/cursos/{theme}-predeterminada.webp'}
            for theme in COVER_THEMES
        ]
        context['widget']['cover_rules'] = COVER_RULES
        return context


WEEKDAYS = [(day, day) for day in (
    'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo',
)]


class CourseScheduleWidget(forms.MultiWidget):
    template_name = 'cursos/widgets/schedule.html'

    def __init__(self, attrs=None):
        super().__init__([
            forms.CheckboxSelectMultiple(choices=WEEKDAYS),
            forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'aria-label': 'Desde'}),
            forms.TimeInput(format='%H:%M', attrs={'type': 'time', 'aria-label': 'Hasta'}),
        ], attrs)

    def decompress(self, value):
        if value:
            match = re.fullmatch(r'(.+) de (\d{2}:\d{2}) a (\d{2}:\d{2})', value)
            if match:
                days = match[1].split(', ')
                if all(day in dict(WEEKDAYS) for day in days):
                    return [days, match[2], match[3]]
        return [[], None, None]


class CourseScheduleField(forms.MultiValueField):
    widget = CourseScheduleWidget

    def __init__(self, **kwargs):
        super().__init__(fields=[
            forms.MultipleChoiceField(choices=WEEKDAYS),
            forms.TimeField(input_formats=['%H:%M']),
            forms.TimeField(input_formats=['%H:%M']),
        ], require_all_fields=True, **kwargs)

    def compress(self, values):
        if not values:
            return ''
        days, start, end = values
        if end <= start:
            raise forms.ValidationError('La hora de fin debe ser posterior a la de inicio.')
        ordered_days = [day for day, _ in WEEKDAYS if day in days]
        return f"{', '.join(ordered_days)} de {start:%H:%M} a {end:%H:%M}"


class CourseSkillsWidget(forms.SelectMultiple):
    template_name = 'cursos/widgets/skills.html'


class CursoForm(forms.ModelForm):
    """Crea o edita los datos y la imagen de un curso."""
    imagen = forms.ImageField(required=False, label="Imagen", widget=CourseImageInput(attrs={"accept": "image/*", "id": "imagen-input"}))
    descripcion = DescripcionField()
    horario = CourseScheduleField(label="Horario")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'input-ien'
        self.fields['imagen'].widget.cover_theme = course_cover_theme(
            self.data.get('nombre', self.initial.get('nombre', '')), cached_category_name(self.instance),
        )
        current = self.initial.get('horario')
        if current and not self.fields['horario'].widget.decompress(current)[0]:
            self.fields['horario'].help_text = (
                f'Horario actual: {current}. Elegí los días y las horas para actualizarlo.'
            )

    class Meta:
        model = Curso
        fields = ['nombre', 'categoria', 'imagen', 'descripcion', 'duracion', 'horario', 'tipo', 'habilidades', 'url_externa']
        labels = {
            'nombre': 'Nombre',
            'categoria': 'Categoría',
            'imagen': 'Imagen',
            'descripcion': 'Descripción',
            'duracion': 'Duración',
            'horario': 'Horario',
            'tipo': 'Modalidad',
            'habilidades': 'Habilidades que desarrolla',
            'url_externa': 'Enlace del curso en el sitio del IEN',
        }
        help_texts = {
            'url_externa': 'Enlace a la página de este curso en el sitio del IEN.',
            'habilidades': 'Agregá las habilidades de a una. Podés quitar cualquiera de la lista.',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nombre del curso'}),
            'categoria': forms.Select(attrs={'class': INPUT_CLASS}),
            'imagen': CourseImageInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-primary/30','id':'imagen-input'}),
            'descripcion': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 4, 'placeholder': 'Descripcion del curso'}),
            'duracion': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Duración del curso'}),

            'tipo': forms.Select(attrs={'class': INPUT_CLASS}),
            'habilidades': CourseSkillsWidget(attrs={'class': INPUT_CLASS}),
            'url_externa': forms.URLInput(attrs={'class': INPUT_CLASS, 'placeholder': 'https://ien.edu.ar/cursos/...'}),
        }

class CategoriaForm(forms.ModelForm):
    """Crea o modifica una categoría mediante su nombre."""
    class Meta:
        model = Categoria
        fields = ['nombre']
        labels = {
            'nombre': 'Nombre',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. Programacion'}),
        }
