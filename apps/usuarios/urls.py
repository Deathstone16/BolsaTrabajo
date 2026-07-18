from django.urls import path
from . import views

urlpatterns = [
    path('registro/', views.registro, name='registro'),
    path('registro-exitoso/', views.registro_exitoso, name='registro_exitoso'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('datos-personales/',views.datos_personales, name='datos_personales'),
    path('datos-personales-exitoso/', views.datos_personales_exitoso, name='datos_personales_exitoso'),
    path('oferente/<int:pk>/', views.perfil_oferente, name='perfil_oferente'),
    path('mi-perfil/', views.mi_perfil, name='mi_perfil'),
    path('eliminar-cv/', views.eliminar_cv, name='eliminar_cv'),
    
    # ── Recuperación de contraseña ────────────────────────────────────────────
    path('recuperar/',                              views.password_reset_request, name='recuperar-contrasena'),
    path('recuperar/enviado/',                      views.recuperacion_enviada,   name='recuperacion-enviada'),
    path('restablecer/<uidb64>/<token>/',           views.password_reset_confirm, name='restablecer-contrasena'),
    path('recuperar/exitoso/',                      views.contrasena_restablecida,name='contrasena-restablecida'),
]