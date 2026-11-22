from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from usuarios.models import Oferente, Usuario
from .models import Oferta
from .services import obtener_ofertas_activas


class BusquedaEmpleoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        empresa = Usuario.objects.create_user(email='busqueda@example.com')
        Oferente.objects.create(
            usuario=empresa, nombre_empresa='Acme Tecnología', cuit='30-12345678-9',
        )
        categoria = Categoria.objects.create(nombre='Sistemas')
        cls.oferta = Oferta.objects.create(
            empresa=empresa, categoria=categoria, titulo='Analista de datos',
            nombre_puesto='Analista', descripcion='Preparación de reportes',
            habilidades_duras='Python', habilidades_blandas='Comunicación',
            habilidades_requeridas='SQL', requisitos_obligatorios='Excel avanzado',
            requisitos_deseables='Power BI', estado='activa', modalidad='remoto',
            experiencia_requerida='2-3', fecha_cierre=timezone.now() + timedelta(days=30),
        )

    def test_matches_company_keywords_and_technical_requirements(self):
        for palabra in ('analista', 'ACME', 'reportes', 'Sistemas', 'Python',
                        'Comunicaci', 'SQL', 'Excel', 'Power BI'):
            with self.subTest(palabra=palabra):
                self.assertQuerySetEqual(obtener_ofertas_activas(palabra), [self.oferta])

    def test_words_combine_across_fields_and_keep_other_filters(self):
        self.assertQuerySetEqual(
            obtener_ofertas_activas('  analista   EXCEL ', 'remoto', '2-3'), [self.oferta],
        )
        self.assertFalse(obtener_ofertas_activas('Excel', 'presencial').exists())
        self.assertFalse(obtener_ofertas_activas('Python', experiencia='5+').exists())
        self.assertFalse(obtener_ofertas_activas('Python carpintería').exists())

    def test_confidential_company_name_is_not_searchable(self):
        self.oferta.es_confidencial = True
        self.oferta.save(update_fields=['es_confidencial'])
        self.assertFalse(obtener_ofertas_activas('Acme').exists())
        self.assertQuerySetEqual(obtener_ofertas_activas('Python'), [self.oferta])

    def test_non_active_offers_are_excluded_for_all_matches(self):
        self.oferta.estado = 'pendiente'
        self.oferta.save(update_fields=['estado'])
        for palabra in ('Acme', 'Python', 'Analista'):
            with self.subTest(palabra=palabra):
                self.assertFalse(obtener_ofertas_activas(palabra).exists())

    def test_public_search_page_finds_skills_and_preserves_query(self):
        response = self.client.get(reverse('buscar_empleo'), {'q': 'Excel'})
        self.assertContains(response, self.oferta.titulo)
        self.assertContains(response, 'value="Excel"')
        self.assertEqual(response.context['total'], 1)

    def test_locality_filter_uses_database_values_and_combines_with_existing_filters(self):
        self.oferta.ubicacion = 'Villa de Prueba, Región de Prueba'
        self.oferta.save(update_fields=['ubicacion'])
        otra = Oferta.objects.create(
            empresa=self.oferta.empresa, categoria=self.oferta.categoria,
            titulo='Otro puesto', nombre_puesto='Analista',
            ubicacion='Otra localidad', descripcion='Python y Excel',
            habilidades_duras='Python', estado='activa', modalidad='remoto',
            experiencia_requerida='2-3', fecha_cierre=self.oferta.fecha_cierre,
        )
        for valor in ('villa de prueba', '  VILLA DE PRUEBA  ', 'Región de Prueba'):
            with self.subTest(ubicacion=valor):
                response = self.client.get(reverse('buscar_empleo'), {
                    'q': 'Excel', 'modalidad': 'remoto', 'experiencia': '2-3',
                    'ubicacion': valor,
                })
                self.assertQuerySetEqual(response.context['ofertas'], [self.oferta])
                self.assertEqual(response.context['ubicacion'], valor)
                self.assertNotContains(response, otra.titulo)
        self.assertFalse(obtener_ofertas_activas(ubicacion='No existe').exists())
        self.assertEqual(obtener_ofertas_activas(ubicacion='   ').count(), 2)
        self.assertFalse(obtener_ofertas_activas(
            'Excel', modalidad='presencial', ubicacion='Villa de Prueba',
        ).exists())

    def test_locality_filter_keeps_confidentiality_and_excludes_non_active_offers(self):
        self.oferta.ubicacion = 'Localidad de Prueba'
        self.oferta.es_confidencial = True
        self.oferta.save(update_fields=['ubicacion', 'es_confidencial'])
        response = self.client.get(reverse('buscar_empleo'), {
            'ubicacion': 'Localidad de Prueba',
        })
        self.assertContains(response, self.oferta.titulo)
        self.assertContains(response, 'Empresa confidencial')
        self.assertNotContains(response, self.oferta.empresa.oferente.nombre_empresa)
        self.oferta.estado = 'pendiente'
        self.oferta.save(update_fields=['estado'])
        self.assertFalse(obtener_ofertas_activas(ubicacion='Localidad de Prueba').exists())
