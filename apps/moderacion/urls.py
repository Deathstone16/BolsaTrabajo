from django.urls import path
from . import views

urlpatterns = [
    path('cursos/', views.listar_cursos, name='mod_listar_cursos'),
    path('cursos/crear/', views.crear_curso, name='mod_crear_curso'),
    path('cursos/<int:curso_id>/modificar/', views.modificar_curso, name='mod_modificar_curso'),
    path('cursos/<int:curso_id>/baja/', views.dar_de_baja_curso, name='mod_dar_de_baja_curso'),
    
    path('categorias/', views.listar_categorias, name='mod_listar_categorias'),
    path('categorias/crear/', views.crear_categoria, name='mod_crear_categoria'),
    path('categorias/<int:categoria_id>/modificar/', views.modificar_categoria, name='mod_modificar_categoria'),
    path('categorias/<int:categoria_id>/baja/', views.dar_de_baja_categoria, name='mod_dar_de_baja_categoria'),

    path('empresas/', views.listar_empresas, name='mod_listar_empresas'),
    path('empresas/<int:pk>/', views.detalle_empresa, name='mod_detalle_empresa'),
    path('empresas/<int:pk>/aprobar/', views.aprobar_empresa, name='mod_aprobar_empresa'),
    path('empresas/<int:pk>/rechazar/', views.rechazar_empresa, name='mod_rechazar_empresa'),
    
    path('ofertas/', views.listar_ofertas, name='mod_listar_ofertas'),
    path('oferta/<int:pk>/detalle/', views.detalle_oferta_json, name='mod_detalle_oferta'),
    path('oferta/<int:pk>/aprobar/', views.aprobar_oferta, name='mod_aprobar_oferta'),
    path('oferta/<int:pk>/rechazar/', views.rechazar_oferta, name='mod_rechazar_oferta'),
    path('oferta/<int:pk>/finalizar/', views.finalizar_oferta, name='mod_finalizar_oferta'),

    path('tipos-oferta/', views.listar_tipos_oferta, name='mod_listar_tipos_oferta'),
    path('tipos-oferta/crear/', views.crear_tipo_oferta, name='mod_crear_tipo_oferta'),
    path('tipos-oferta/<int:tipo_id>/modificar/', views.modificar_tipo_oferta, name='mod_modificar_tipo_oferta'),
    path('tipos-oferta/<int:tipo_id>/baja/', views.eliminar_tipo_oferta, name='mod_eliminar_tipo_oferta'),
]