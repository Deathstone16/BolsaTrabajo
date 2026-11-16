from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Curso


class CatalogoFiltrosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tecnologia = Categoria.objects.create(nombre='Tecnología')
        cls.gestion = Categoria.objects.create(nombre='Gestión')
        cls.retirada = Categoria.objects.create(nombre='Retirada')
        cls.excel = Curso.objects.create(
            nombre='Excel inicial', categoria=cls.tecnologia,
            duracion='8 semanas', tipo=Curso.VIRTUAL,
        )
        cls.excel_presencial = Curso.objects.create(
            nombre='Excel avanzado', categoria=cls.gestion,
            duracion='4 semanas', tipo=Curso.PRESENCIAL,
        )
        Curso.objects.create(
            nombre='Excel retirado', categoria=cls.retirada,
            duracion='99 semanas', activo=False,
        )

    def test_title_search_and_each_filter_can_be_combined(self):
        for filtros in (
            {'q': '  EXCEL inicial  '},
            {'categoria': self.tecnologia.pk},
            {'modalidad': Curso.VIRTUAL},
            {'duracion': '8 semanas'},
            {'q': 'excel', 'categoria': self.tecnologia.pk,
             'modalidad': Curso.VIRTUAL, 'duracion': '8 semanas'},
        ):
            with self.subTest(filtros=filtros):
                response = self.client.get(reverse('cursos:listado'), filtros)
                self.assertQuerySetEqual(response.context['cursos'], [self.excel])
                self.assertContains(response, '1 curso encontrado')
                self.assertContains(response, 'Limpiar filtros')

    def test_unfiltered_catalog_and_options_only_include_active_courses(self):
        response = self.client.get(reverse('cursos:listado'))
        self.assertEqual(response.context['total_resultados'], 2)
        self.assertNotContains(response, 'Excel retirado')
        self.assertNotContains(response, 'Retirada')
        self.assertNotContains(response, '99 semanas')
        self.assertNotContains(response, 'Limpiar filtros')

    def test_no_matches_preserves_search_and_offers_reset(self):
        response = self.client.get(reverse('cursos:listado'), {'q': 'carpintería'})
        self.assertContains(response, 'No encontramos cursos con esos filtros.')
        self.assertContains(response, 'value="carpintería"')
        self.assertContains(response, 'Limpiar filtros')

    def test_invalid_filter_values_show_validation_without_server_error(self):
        for filtros in ({'categoria': 'abc'}, {'categoria': '9' * 100},
                        {'modalidad': 'inventada'}, {'duracion': '99 semanas'}):
            with self.subTest(filtros=filtros):
                response = self.client.get(reverse('cursos:listado'), filtros)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['filtros'].errors)
                self.assertContains(response, 'Revisá los filtros')
