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


class CursoForm(forms.ModelForm):
    """Crea o edita los datos y la imagen de un curso."""
    descripcion = DescripcionField()
    class Meta:
        model = Curso
        fields = ['nombre', 'categoria', 'imagen', 'descripcion', 'duracion', 'horario', 'tipo', 'habilidades', 'url_externa']
        labels = {
            'nombre': 'Nombre',
            'categoria': 'Categoria',
            'imagen': 'Imagen',
            'descripcion': 'Descripcion',
            'duracion': 'Duracion',
            'horario': 'Horario',
            'tipo': 'Tipo',
            'habilidades': 'Habilidades que desarrolla',
            'url_externa': 'Enlace del curso en el sitio del IEN',
        }
        help_texts = {
            'url_externa': 'Opcional. Pegá la URL de la página específica de este curso en el sitio del IEN. Se usa en el botón «Ver curso en el IEN».',
            'habilidades': 'Seleccioná competencias que el curso desarrolla. Esto ayuda a recomendar opciones generales sin asumir contenidos no declarados.',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. Python desde cero'}),
            'categoria': forms.Select(attrs={'class': INPUT_CLASS}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'w-full px-4 py-2 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-primary/30','id':'imagen-input'}),
            'descripcion': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 4, 'placeholder': 'Descripcion del curso'}),
            'duracion': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. 6 meses'}),
            'horario': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ej. Lunes y Miercoles 18:00 - 21:00'}),
            'tipo': forms.Select(attrs={'class': INPUT_CLASS}),
            'habilidades': forms.SelectMultiple(attrs={'class': INPUT_CLASS, 'size': 8}),
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
