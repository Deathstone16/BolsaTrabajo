from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Postulante, Oferente

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
    pass

@admin.register(Oferente)
class OferenteAdmin(admin.ModelAdmin):
    pass