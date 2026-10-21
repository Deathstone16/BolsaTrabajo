from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from .models import Usuario, Postulante, Oferente
from .uploads import normalize_image_upload


class PostulanteAdminForm(forms.ModelForm):
    class Meta:
        model = Postulante
        fields = '__all__'

    def clean_foto(self):
        upload = self.cleaned_data.get('foto')
        return normalize_image_upload(upload, max_bytes=2 * 1024 * 1024, max_side=1024) if upload and hasattr(upload, 'read') else upload


class OferenteAdminForm(forms.ModelForm):
    class Meta:
        model = Oferente
        fields = '__all__'

    def clean_logo(self):
        upload = self.cleaned_data.get('logo')
        return normalize_image_upload(upload, max_bytes=2 * 1024 * 1024) if upload and hasattr(upload, 'read') else upload

    def clean_banner(self):
        upload = self.cleaned_data.get('banner')
        return normalize_image_upload(upload, max_bytes=5 * 1024 * 1024) if upload and hasattr(upload, 'read') else upload

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ['email']
    list_display = ['email', 'first_name', 'last_name', 'is_staff']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('first_name', 'last_name')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )

@admin.register(Postulante)
class PostulanteAdmin(admin.ModelAdmin):
    form = PostulanteAdminForm
    readonly_fields = ('cv', 'cv_version_actual', 'cv_fecha_carga')

@admin.register(Oferente)
class OferenteAdmin(admin.ModelAdmin):
    form = OferenteAdminForm
