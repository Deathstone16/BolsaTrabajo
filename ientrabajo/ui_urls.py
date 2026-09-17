"""URLs de la interfaz nueva, montadas bajo /ui/.

Los nombres llevan sufijo _ui para que convivan con los originales sin pisarlos.
"""

from django.urls import path

from . import ui_views

urlpatterns = [
    path('', ui_views.home, name='home_ui'),
    path('buscar/', ui_views.buscar_empleo, name='buscar_empleo_ui'),
    path('oferta/<int:pk>/', ui_views.detalle_oferta, name='detalle_oferta_ui'),
]
