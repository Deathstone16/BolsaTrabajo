from django.urls import path

from . import views

app_name = 'ia'

urlpatterns = [
    path('solicitar-analisis/', views.solicitar_analisis, name='solicitar_analisis'),
    path('analisis/<int:analisis_id>/estado/', views.estado_analisis, name='estado_analisis'),
    path('analisis/<int:analisis_id>/', views.ver_resultado, name='ver_resultado'),
    path('llegue/', views.llegue, name='llegue'),
]
