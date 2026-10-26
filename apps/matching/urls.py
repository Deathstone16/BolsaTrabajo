from django.urls import path

from . import views


app_name = 'matching'
urlpatterns = [
    path('ofertas/<int:oferta_id>/calcular/', views.calcular_compatibilidad, name='calcular'),
    path('estado/<uuid:request_id>/', views.estado_compatibilidad, name='estado'),
    path('cancelar/<uuid:request_id>/', views.cancelar_compatibilidad, name='cancelar'),
    path('resultado/<uuid:request_id>/', views.detalle_compatibilidad, name='detalle'),
]
