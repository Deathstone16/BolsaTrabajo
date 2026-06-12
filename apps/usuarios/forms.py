from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario, Postulante, Oferente



class RegistroBaseForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ['email', 'password1', 'password2']


class RegistroPostulanteForm(RegistroBaseForm):
    class Meta(RegistroBaseForm.Meta):
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
        }

    def save(self, commit=True):
        user = super().save(commit=True)
        Postulante.objects.create(usuario=user)
        return user


class RegistroOferenteForm(RegistroBaseForm):
    nombre_empresa = forms.CharField(max_length=200, label='Nombre de la empresa')
    cuit = forms.CharField(max_length=13, label='CUIT')

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
    
class OferenteForm(forms.ModelForm):
    class Meta:
        model = Oferente
        fields = [
            'nombre_empresa', 'cuit', 'descripcion', 'industria',
            'tamano_empresa', 'ubicacion', 'anio_fundacion',
            'sitio_web', 'telefono', 'logo', 'banner'
        ]

class DatosPersonalesForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, label='Nombre')
    last_name = forms.CharField(max_length=150, label='Apellido')
    email = forms.EmailField(label="Email")
    dni = forms.CharField(max_length=8, label='DNI')
    fecha_nacimiento = forms.DateField(
        label='Fecha de nacimiento',
        widget=forms.DateInput(attrs={'type':'date'})
    )
    telefono=forms.CharField(max_length=20, label='Teléfono')
    direccion=forms.CharField(max_length=200, label='Dirección')
    
    class Meta:
        model = Postulante
        fields = ['dni','fecha_nacimiento','telefono','direccion']
        
    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if not dni.isdigit():
            raise forms.ValidationError('El DNI solo puede contener números.')
        if len(dni) != 8:
            raise forms.ValidationError('El DNI debe tener 8 dígitos.')
        return dni

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not telefono.isdigit():
            raise forms.ValidationError('El teléfono solo puede contener números.')
        return telefono
    
    
    
