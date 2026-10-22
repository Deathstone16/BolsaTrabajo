from django.contrib import admin
from .models import Curso


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'activo')
    list_filter = ('activo', 'categoria')
    filter_horizontal = ('habilidades',)
