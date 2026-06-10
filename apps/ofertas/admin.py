from django.contrib import admin
from .models import Oferta, CategoriaOferta

@admin.register(Oferta)
class OfertaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'empresa', 'estado', 'fecha_publicacion')
    list_filter = ('estado', 'modalidad')
    search_fields = ('titulo', 'nombre_puesto')

@admin.register(CategoriaOferta)
class CategoriaOfertaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)