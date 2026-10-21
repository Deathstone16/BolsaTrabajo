from django.urls import path
from . import views

app_name = 'cursos'
urlpatterns = [
    path('', views.listado, name='listado'),
    path('<int:pk>/', views.detalle, name='detalle'),
]
