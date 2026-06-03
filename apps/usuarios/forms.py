from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario

class RegistroForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ['nombre_completo', 'tipo', 'email', 'password1', 'password2','cuit']

    def clean(self):
        cleanded_data = super().clean()
        tipo = cleanded_data.get('tipo')
        cuit = cleanded_data.get('cuit')

        if tipo == Usuario.OFERENTE and not cuit:
            raise forms.ValidationError('El campo CUIT es obligatorio para oferentes.')
        
        return cleanded_data
