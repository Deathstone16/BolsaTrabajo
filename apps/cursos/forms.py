"""Formularios administrativos para cursos y categorías."""

from ientrabajo.form_fields import DescripcionField
from django import forms
from .models import Curso, Categoria

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


class CursoForm(forms.ModelForm):
    """Crea o edita los datos y la imagen de un curso."""
    descripcion = DescripcionField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'input-ien'

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
            'habilidades': 'Seleccioná las habilidades del curso. Usá Ctrl o Cmd para elegir varias.',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nombre del curso'}),
            'categoria': forms.Select(attrs={'class': INPUT_CLASS}),
            'imagen': CourseImageInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-primary/30','id':'imagen-input'}),
            'descripcion': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 4, 'placeholder': 'Descripcion del curso'}),
            'duracion': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Duración del curso'}),
            'horario': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Días y horarios'}),
            'tipo': forms.Select(attrs={'class': INPUT_CLASS}),
            'habilidades': forms.SelectMultiple(attrs={'class': INPUT_CLASS, 'size': 4}),
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
