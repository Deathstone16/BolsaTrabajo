"""
Formularios de la app de moderación.

Define formularios utilizados en el panel de administración,
como el formulario de rechazo de empresas.
"""

from django import forms

class RechazarEmpresaForm(forms.Form):
    """Formulario para que el moderador escriba el motivo de rechazo de una empresa.

    Attributes:
        motivo_rechazo: Textarea con el motivo del rechazo.
    """
    motivo_rechazo = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Ej: El CUIT no se corresponde con la empresa declarada...'
        }),
        label='Motivo del rechazo',
        help_text='Explicá al oferente por qué se rechaza su registro.',
    )