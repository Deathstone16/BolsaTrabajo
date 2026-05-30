from django.contrib import admin

# Register your models here.

from .models import Curso, Categoria
admin.site.register(Curso)
admin.site.register(Categoria)
