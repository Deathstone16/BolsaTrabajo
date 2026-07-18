from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm as DjangoSetPasswordForm
from .models import Usuario, Postulante, Oferente

CV_FORMATOS_PERMITIDOS = ['pdf', 'doc', 'docx']
CV_TAMANO_MAXIMO_MB = 5



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

    


class RegistroOferenteForm(RegistroBaseForm):
    nombre_empresa = forms.CharField(max_length=200, label='Nombre de la empresa')
    cuit = forms.CharField(max_length=13, label='CUIT')



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


# ─── Formularios nuevos: recuperación de contraseña ──────────────────────────

class PasswordResetRequestForm(forms.Form):
    """
    Paso 1: el usuario ingresa su email.
    No revela si el correo existe (seguridad por oscuridad).
    """
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 rounded-lg border border-border bg-input-background '
                     'focus:outline-none focus:ring-2 focus:ring-primary/30',
            'placeholder': 'tu@email.com',
            'autofocus': True,
        })
    )

    def get_usuario(self):
        """Retorna el Usuario si el email existe, o None. Sin excepciones."""
        email = self.cleaned_data.get('email', '').lower()
        try:
            return Usuario.objects.get(email__iexact=email)
        except Usuario.DoesNotExist:
            return None


class SetPasswordForm(DjangoSetPasswordForm):
    """
    Paso 3: nueva contraseña. Extiende el built-in de Django
    con los estilos Tailwind del proyecto.
    """
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 rounded-lg border border-border bg-input-background '
                     'focus:outline-none focus:ring-2 focus:ring-primary/30 pr-10',
            'placeholder': 'Mínimo 8 caracteres',
            'id': 'nueva_contrasena',
        }),
    )
    new_password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 rounded-lg border border-border bg-input-background '
                     'focus:outline-none focus:ring-2 focus:ring-primary/30 pr-10',
            'placeholder': 'Repetí la contraseña',
            'id': 'confirmar_contrasena',
        }),
    )


class CargaCVForm(forms.Form):
    cv = forms.FileField(label='Archivo CV')

    def clean_cv(self):
        archivo = self.cleaned_data.get('cv')
        if not archivo:
            raise forms.ValidationError('Debes seleccionar un archivo.')

        extension = archivo.name.rsplit('.', 1)[-1].lower()
        if extension not in CV_FORMATOS_PERMITIDOS:
            raise forms.ValidationError(
                f'Formato no permitido. Solo se aceptan: {", ".join(CV_FORMATOS_PERMITIDOS).upper()}'
            )

        tamano_bytes = archivo.size
        tamano_maximo_bytes = CV_TAMANO_MAXIMO_MB * 1024 * 1024
        if tamano_bytes > tamano_maximo_bytes:
            raise forms.ValidationError(
                f'El archivo supera el tamaño máximo de {CV_TAMANO_MAXIMO_MB} MB.'
            )

        return archivo
