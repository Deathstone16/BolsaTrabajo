from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.crypto import get_random_string

from .configuration import publish_configuration
from .models import ConfiguracionActiva, ConfiguracionCompatibilidad, ResultadoCompatibilidad


@admin.register(ConfiguracionCompatibilidad)
class ConfiguracionCompatibilidadAdmin(admin.ModelAdmin):
    list_display = ('version', 'es_borrador', 'creada_por', 'publicada_por', 'publicada_en')
    fields = (
        'version', 'technical_skills', 'soft_skills', 'experience', 'education',
        'languages', 'logistics', 'desirables', 'es_borrador', 'creada_por',
        'publicada_por', 'creada_en', 'publicada_en',
    )
    readonly_fields = ('creada_por', 'publicada_por', 'creada_en', 'publicada_en')
    actions = ('publicar_seleccionada', 'duplicar_como_borrador', 'restaurar_valores_iniciales')
    change_form_template = 'admin/matching/configuracioncompatibilidad/change_form.html'

    class Media:
        js = ('matching/configuration_total.js',)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        # Publicar sólo puede hacerlo el servicio transaccional, nunca un checkbox.
        fields.append('es_borrador')
        if obj and not obj.es_borrador:
            fields.extend(field.name for field in obj._meta.fields)
        return tuple(dict.fromkeys(fields))

    def render_change_form(self, request, context, *args, **kwargs):
        context['puede_publicar_configuracion'] = bool(
            request.user.is_superuser
            or request.user.has_perm('matching.publicar_configuracioncompatibilidad')
        )
        return super().render_change_form(request, context, *args, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creada_por = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Publicar configuración seleccionada')
    def publicar_seleccionada(self, request, queryset):
        if not request.user.is_superuser and not request.user.has_perm('matching.publicar_configuracioncompatibilidad'):
            self.message_user(request, 'No tenés permiso para publicar la configuración.', messages.ERROR)
            return
        if queryset.count() != 1:
            self.message_user(request, 'Seleccioná una sola configuración para publicar.', messages.ERROR)
            return
        try:
            publish_configuration(queryset.first().pk, request.user)
        except (ValidationError, ValueError) as exc:
            self.message_user(request, '; '.join(getattr(exc, 'messages', [str(exc)])), messages.ERROR)
        else:
            self.message_user(request, 'La configuración quedó publicada y activa.', messages.SUCCESS)

    @admin.action(description='Duplicar como borrador')
    def duplicar_como_borrador(self, request, queryset):
        for config in queryset:
            defaults = {field: getattr(config, field) for field in ConfiguracionCompatibilidad.FIELDS}
            ConfiguracionCompatibilidad.objects.create(
                version=f'draft-{get_random_string(12).lower()}',
                creada_por=request.user,
                es_borrador=True,
                **defaults,
            )
        self.message_user(request, 'Se crearon borradores para editar.', messages.SUCCESS)

    @admin.action(description='Crear borrador con valores iniciales')
    def restaurar_valores_iniciales(self, request, queryset):
        ConfiguracionCompatibilidad.objects.create(
            version=f'defaults-{get_random_string(12).lower()}',
            creada_por=request.user,
            es_borrador=True,
        )
        self.message_user(request, 'Se creó un borrador con valores 35/15/20/10/5/5/10.', messages.SUCCESS)

    def has_delete_permission(self, request, obj=None):
        return bool(not obj or obj.es_borrador) and super().has_delete_permission(request, obj)

    def delete_queryset(self, request, queryset):
        borradores = queryset.filter(es_borrador=True)
        publicados = queryset.filter(es_borrador=False).count()
        borradores.delete()
        if publicados:
            self.message_user(request, 'No se eliminaron configuraciones publicadas.', messages.ERROR)

    def response_change(self, request, obj):
        if '_publicar_configuracion' in request.POST:
            if obj.es_borrador:
                try:
                    publish_configuration(obj.pk, request.user)
                except (PermissionDenied, ValidationError, ValueError) as exc:
                    self.message_user(request, '; '.join(getattr(exc, 'messages', [str(exc)])), messages.ERROR)
                else:
                    self.message_user(request, 'La configuración quedó publicada y activa.', messages.SUCCESS)
            return super().response_change(request, obj)
        return super().response_change(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        if '_publicar_configuracion' in request.POST:
            try:
                publish_configuration(obj.pk, request.user)
            except (PermissionDenied, ValidationError, ValueError) as exc:
                self.message_user(request, '; '.join(getattr(exc, 'messages', [str(exc)])), messages.ERROR)
            else:
                self.message_user(request, 'La configuración quedó publicada y activa.', messages.SUCCESS)
        return super().response_add(request, obj, post_url_continue)


@admin.register(ConfiguracionActiva)
class ConfiguracionActivaAdmin(admin.ModelAdmin):
    list_display = ('singleton', 'configuracion')
    readonly_fields = ('singleton', 'configuracion')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ResultadoCompatibilidad)
class ResultadoCompatibilidadAdmin(admin.ModelAdmin):
    list_display = ('id', 'postulante', 'oferta', 'estado', 'match_percentage', 'actualizado_en')
    readonly_fields = ('request_id', 'cache_key', 'creado_en', 'actualizado_en')
