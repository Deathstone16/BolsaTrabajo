from django.contrib import admin

from .models import ResultadoCompatibilidad


@admin.register(ResultadoCompatibilidad)
class ResultadoCompatibilidadAdmin(admin.ModelAdmin):
    list_display = ('id', 'postulante', 'oferta', 'estado', 'match_percentage', 'actualizado_en')
    readonly_fields = ('request_id', 'cache_key', 'creado_en', 'actualizado_en')
