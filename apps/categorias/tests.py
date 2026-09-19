from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from cursos import services as cursos_services
from categorias.models import Categoria as CategoriaActual, Habilidad as HabilidadActual


class CategoriaProtegidaTests(TestCase):
    def test_no_elimina_categoria_que_tiene_habilidades(self):
        categoria = CategoriaActual.objects.create(nombre='Tecnología')
        HabilidadActual.objects.create(nombre='Python', categoria=categoria)

        resultado = cursos_services.dar_de_baja_categoria(categoria.id)

        self.assertIsNone(resultado)
        self.assertTrue(CategoriaActual.objects.filter(id=categoria.id).exists())


class HabilidadesHeredadasMigrationTests(TransactionTestCase):
    """Comprueba que la migración conserva habilidades con datos antiguos."""

    desde = [
        ('categorias', '0004_alter_habilidad_unique_together_and_more'),
        ('ofertas', '0010_remove_oferta_tipo_oferta'),
    ]

    def test_conserva_tipos_y_habilidades_sin_tipo(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.desde)
        modelos = executor.loader.project_state(self.desde).apps
        Categoria = modelos.get_model('categorias', 'Categoria')
        TipoOferta = modelos.get_model('categorias', 'TipoOferta')
        Habilidad = modelos.get_model('categorias', 'Habilidad')

        Categoria.objects.create(id=7, nombre='Tecnología')
        tipo = TipoOferta.objects.create(nombre='Tecnología')
        Habilidad.objects.create(nombre='Python', tipo_oferta=tipo)
        Habilidad.objects.create(nombre='Comunicación', tipo_oferta=None)
        Habilidad.objects.create(nombre='Comunicación', tipo_oferta=None)

        try:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            Habilidad = executor.loader.project_state().apps.get_model('categorias', 'Habilidad')
            self.assertEqual(
                Habilidad.objects.get(nombre='Python').categoria.nombre,
                'Tecnología',
            )
            categorias = list(
                Habilidad.objects.filter(nombre='Comunicación')
                .values_list('categoria__nombre', flat=True)
            )
            self.assertEqual(len(categorias), 2)
            self.assertEqual(len(set(categorias)), 2)
            self.assertIn('Sin categoría', categorias)
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
