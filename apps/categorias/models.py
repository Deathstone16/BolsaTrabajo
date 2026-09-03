"""
Modelos de categorías y habilidades.

Define ``Categoria`` para clasificar ofertas y cursos,
y ``Habilidad`` para las competencias requeridas.
"""

from django.db import models


class TipoOferta(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Tipo de Oferta"
        verbose_name_plural = "Tipos de Ofertas"

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    """Categoría para clasificar ofertas laborales y cursos."""
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre


class Habilidad(models.Model):
    """Habilidad (blanda o dura) asociada a una categoría."""
    HABILIDAD_CHOICES = [
        ('B', 'Blandas'),
        ('D', 'Duras'),
    ]

    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    tipo_oferta = models.ForeignKey(
        TipoOferta, null=True, blank=True, on_delete=models.SET_NULL
    )
    nombre = models.CharField(max_length=100)
    tipo_habilidad = models.CharField(max_length=1, choices=HABILIDAD_CHOICES, default='D')

    class Meta:
        verbose_name = "Habilidad"
        verbose_name_plural = "Habilidades"
        unique_together = ('nombre', 'categoria')

    def __str__(self):
        return f"{self.nombre} ({self.categoria.nombre})"
