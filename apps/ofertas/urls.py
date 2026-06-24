from django.urls import path
from . import views

urlpatterns = [
    path('crear/', views.crear_oferta, name='crear_oferta'),
    path('dashboard/', views.dashboard_empresa, name='dashboard_empresa'),
    path('editar/<int:pk>/', views.editar_oferta, name='editar_oferta'),
    path('eliminar/<int:pk>/', views.eliminar_oferta, name='eliminar_oferta'),
    path('editar-perfil/', views.editar_perfil_empresa, name='editar_perfil_empresa'),
    path('datos/<int:pk>/', views.datos_oferta, name='datos_oferta'),
    path('lista-parcial/', views.lista_ofertas_parcial, name='lista_ofertas_parcial'),
    path('validacion-pendiente/', views.validacion_pendiente, name='validacion_pendiente'),
]