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
    
]