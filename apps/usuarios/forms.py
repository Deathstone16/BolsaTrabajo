from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario, Postulante, Oferente


class RegistroPostulanteForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
        }

    def save(self, commit=True):
        user = super().save(commit=True)
        Postulante.objects.create(usuario=user)
        return user
    
    
class RegistroOferenteForm(UserCreationForm):
    nombre_empresa = forms.CharField(max_length=200, label='Nombre de la empresa')
    cuit = forms.CharField(max_length=13, label='CUIT')

    class Meta:
        model = Usuario
        fields = ['email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=True)
        Oferente.objects.create(
            usuario=user,
            nombre_empresa=self.cleaned_data['nombre_empresa'],
            cuit=self.cleaned_data['cuit']
        )
        return user

class LoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput()
    )