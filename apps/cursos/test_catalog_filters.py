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


class CatalogoPaginacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nombre='Tecnología de prueba')
        cls.cursos = [
            Curso.objects.create(
                nombre=f'SQL {numero:02d}', categoria=cls.categoria,
                descripcion='Capacitación de prueba.', duracion='8 semanas',
                horario='A coordinar', tipo=Curso.VIRTUAL,
            )
            for numero in range(1, 14)
        ]
        cls.otro = Curso.objects.create(
            nombre='Taller presencial', categoria=cls.categoria,
            duracion='4 semanas', tipo=Curso.PRESENCIAL,
        )
        Curso.objects.create(
            nombre='SQL retirado', categoria=cls.categoria,
            duracion='8 semanas', tipo=Curso.VIRTUAL, activo=False,
        )

    def test_all_active_courses_can_be_reached_without_duplicates(self):
        primera = self.client.get(reverse('cursos:listado'))
        segunda = self.client.get(reverse('cursos:listado'), {'page': 2})
        ids_primera = {curso.pk for curso in primera.context['cursos']}
        ids_segunda = {curso.pk for curso in segunda.context['cursos']}
        self.assertEqual(len(ids_primera), 12)
        self.assertEqual(len(ids_segunda), 2)
        self.assertFalse(ids_primera & ids_segunda)
        self.assertEqual(ids_primera | ids_segunda, {curso.pk for curso in self.cursos} | {self.otro.pk})
        self.assertEqual(segunda.context['total_resultados'], 14)
        self.assertContains(primera, 'page=2#cursos-resultados')
        self.assertContains(segunda, 'page=1#cursos-resultados')
        self.assertNotContains(segunda, 'SQL retirado')

    def test_filters_are_applied_before_pagination_and_remain_in_links(self):
        filtros = {'q': 'SQL', 'categoria': self.categoria.pk,
                   'modalidad': Curso.VIRTUAL, 'duracion': '8 semanas', 'page': 2}
        response = self.client.get(reverse('cursos:listado'), filtros)
        self.assertQuerySetEqual(response.context['cursos'], [self.cursos[-1]])
        self.assertEqual(response.context['total_resultados'], 13)
        self.assertNotContains(response, self.otro.nombre)
        self.assertContains(response, 'aria-current="page"')
        from urllib.parse import parse_qs
        self.assertEqual(parse_qs(response.context['pagination_query']), {
            'q': ['SQL'], 'categoria': [str(self.categoria.pk)],
            'modalidad': [Curso.VIRTUAL], 'duracion': ['8 semanas'],
        })
        primera = self.client.get(reverse('cursos:listado'), {
            key: value for key, value in filtros.items() if key != 'page'
        })
        self.assertEqual(primera.context['pagina'].number, 1)
        self.assertEqual(len(primera.context['cursos']), 12)

    def test_home_shows_four_active_courses_and_links_to_full_catalog(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(len(response.context['cursos']), 4)
        self.assertContains(response, 'Ver todos los cursos')
        self.assertNotContains(response, 'SQL retirado')

    def test_invalid_or_out_of_range_page_does_not_break_catalog(self):
        for page in ('texto', '99999', '0'):
            with self.subTest(page=page):
                response = self.client.get(reverse('cursos:listado'), {'page': page})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['cursos'])
