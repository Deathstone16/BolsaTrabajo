from django import forms

class RechazarEmpresaForm(forms.Form):
    motivo_rechazo = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Ej: El CUIT no se corresponde con la empresa declarada...'
        }),
        label='Motivo del rechazo',
        help_text='Explicá al oferente por qué se rechaza su registro.',
    )