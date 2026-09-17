from django.urls import path

from . import views

app_name = 'ia'

urlpatterns = [
    path('solicitar-analisis/', views.solicitar_analisis, name='solicitar_analisis'),
    path('llegue/', views.llegue, name='llegue'),
]
