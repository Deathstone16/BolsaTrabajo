import logging

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.db import transaction
from django.urls import reverse
from .models import Usuario, Postulante, Oferente
from .uploads import normalize_image_upload
from . import services


logger = logging.getLogger(__name__)


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

    def save_model(self, request, obj, form, change):
        estado_anterior = None
        if change:
            estado_anterior = Oferente.objects.filter(pk=obj.pk).values_list(
                'estado_validacion', flat=True
            ).first()
        super().save_model(request, obj, form, change)
        if (estado_anterior != Oferente.EstadoValidacion.APROBADO
                and obj.estado_validacion == Oferente.EstadoValidacion.APROBADO):
            dashboard_url = request.build_absolute_uri(reverse('dashboard_empresa'))

            def notificar():
                try:
                    services.enviar_email_aprobacion(obj, dashboard_url)
                except Exception:
                    logger.exception('No se pudo enviar el aviso de aprobación para la empresa %s.', obj.pk)

            transaction.on_commit(notificar)
