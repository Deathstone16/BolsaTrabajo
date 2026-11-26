"""Formularios de autenticación, perfiles y archivos de usuarios."""

import re

from ientrabajo.form_fields import DescripcionField
from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm as DjangoSetPasswordForm
from .models import Usuario, Postulante, Oferente
from .validators import normalizar_cuit, validar_cuit
from .uploads import normalize_image_upload, validate_cv_upload

CV_FORMATOS_PERMITIDOS = ['pdf', 'docx', 'odt', 'txt']
CV_TAMANO_MAXIMO_MB = 5


class CuitField(forms.CharField):
    """Acepta el CUIT de la empresa con o sin guiones y explica el formato."""

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 13)
        kwargs.setdefault('label', 'CUIT de la empresa')
        kwargs.setdefault('help_text', 'Ingresá los 11 números del CUIT. Los guiones se agregan automáticamente.')
        kwargs.setdefault('error_messages', {
            'required': 'Ingresá el CUIT de tu empresa.',
            'max_length': 'El CUIT debe tener 11 números, con o sin guiones.',
        })
        kwargs.setdefault('widget', forms.TextInput(attrs={
            'inputmode': 'numeric',
            'autocomplete': 'off',
            'placeholder': 'XX-XXXXXXXX-X',
        }))
        super().__init__(**kwargs)

    def validate(self, value):
        super().validate(value)
        if value and not re.fullmatch(r'(?:[0-9]{11}|[0-9]{2}-[0-9]{8}-[0-9])', value):
            if len(re.sub(r'\D', '', value)) != 11:
                raise forms.ValidationError('El CUIT debe tener 11 números. Revisá que esté completo.')
            raise forms.ValidationError('Escribí el CUIT con o sin guiones, con el formato XX-XXXXXXXX-X.')



class RegistroBaseForm(UserCreationForm):
    """Formulario base para crear usuarios cuyo identificador es el email."""
    class Meta:
        model = Usuario
        fields = ['email', 'password1', 'password2']
        error_messages = {'email': {'unique': 'Este correo ya tiene una cuenta. Iniciá sesión o recuperá tu contraseña.'}}


class RegistroPostulanteForm(RegistroBaseForm):
    """Registra un postulante junto con nombre y apellido."""
    class Meta(RegistroBaseForm.Meta):
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
        }

    


class RegistroOferenteForm(RegistroBaseForm):
    """Registra una cuenta empresarial con nombre comercial y CUIT."""
    nombre_empresa = forms.CharField(max_length=200, label='Nombre de la empresa')
    cuit = CuitField()
    contacto_nombre = forms.CharField(
        max_length=150,
        label='Nombre del responsable',
        help_text='Persona responsable o referente de RRHH de la empresa.',
        strip=True,
    )
    contacto_cargo = forms.CharField(
        max_length=100,
        label='Cargo o área del responsable',
    )
    correo_publico = forms.EmailField(
        max_length=254,
        label='Correo de contacto público',
        help_text='Se muestra en el perfil de la empresa. Puede ser distinto del correo de acceso.',
    )

    def clean_cuit(self):
        cuit = self.cleaned_data['cuit']
        validar_cuit(cuit)
        return normalizar_cuit(cuit)

    def clean_contacto_nombre(self):
        nombre = self.cleaned_data.get('contacto_nombre', '').strip()
        if not nombre:
            raise forms.ValidationError('Ingresá el nombre de la persona responsable de la empresa.')
        return nombre

class LoginForm(forms.Form):
    """Recibe las credenciales utilizadas por el servicio de autenticación."""
    email = forms.EmailField(label='Email')
    password = forms.CharField(
        label='Contraseña',
        strip=False,
        widget=forms.PasswordInput()
    )
    
class OferenteForm(forms.ModelForm):
    """Edita la información pública y de contacto de una empresa."""
    descripcion = DescripcionField(required=False)
    cuit = CuitField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['contacto_cargo'].required = True
        self.fields['correo_publico'].required = True

    class Meta:
        model = Oferente
        fields = [
            'nombre_empresa', 'cuit', 'descripcion', 'industria',
            'tamano_empresa', 'ubicacion', 'anio_fundacion',
            'sitio_web', 'telefono', 'logo', 'banner',
            'contacto_nombre', 'contacto_cargo', 'correo_publico',
        ]
        widgets = {
            'contacto_nombre': forms.TextInput(attrs={'class': 'input-ien', 'placeholder': 'Nombre completo'}),
            'contacto_cargo': forms.TextInput(attrs={'class': 'input-ien', 'placeholder': 'Cargo o área'}),
            'correo_publico': forms.EmailInput(attrs={'class': 'input-ien', 'placeholder': 'Correo de contacto'}),
        }

    def clean_cuit(self):
        cuit = self.cleaned_data['cuit']
        validar_cuit(cuit)
        return normalizar_cuit(cuit)

    def clean_logo(self):
        upload = self.cleaned_data.get('logo')
        if upload and hasattr(upload, 'read'):
            return normalize_image_upload(upload, max_bytes=2 * 1024 * 1024)
        return upload

    def clean_banner(self):
        upload = self.cleaned_data.get('banner')
        if upload and hasattr(upload, 'read'):
            return normalize_image_upload(upload, max_bytes=5 * 1024 * 1024)
        return upload

class DatosPersonalesForm(forms.ModelForm):
    """Actualiza datos del usuario y del perfil de postulante."""
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
        """Exige un DNI compuesto exactamente por ocho dígitos."""
        dni = self.cleaned_data.get('dni')
        if not dni.isdigit():
            raise forms.ValidationError('El DNI solo puede contener números.')
        if len(dni) != 8:
            raise forms.ValidationError('El DNI debe tener 8 dígitos.')
        return dni

    def clean_telefono(self):
        """Impide almacenar caracteres no numéricos en el teléfono."""
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
            'class': 'input-ien',
            'autocomplete': 'email',
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
            'class': 'input-ien password-input',
            'autocomplete': 'new-password',
            'placeholder': 'Mínimo 8 caracteres',
            'id': 'nueva_contrasena',
        }),
    )
    new_password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'input-ien password-input',
            'autocomplete': 'new-password',
            'placeholder': 'Repetí la contraseña',
            'id': 'confirmar_contrasena',
        }),
    )


class CargaCVForm(forms.Form):
    """Valida formato y tamaño del archivo de currículum."""
    cv = forms.FileField(label='Archivo CV')

    def clean_cv(self):
        """Acepta solo formatos con soporte de extracción habilitado."""
        archivo = self.cleaned_data.get('cv')
        if not archivo:
            raise forms.ValidationError('Debes seleccionar un archivo.')

        try:
            validate_cv_upload(archivo)
        except Exception as exc:
            if hasattr(exc, 'messages'):
                raise forms.ValidationError(exc.messages)
            raise

        return archivo
