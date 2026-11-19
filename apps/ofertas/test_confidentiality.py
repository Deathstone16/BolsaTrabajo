from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from usuarios.models import Oferente, Postulante, Usuario

from .models import Oferta


class ConfidencialidadOfertaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Usuario.objects.create_user(email='empresa-confidencial@example.invalid')
        cls.oferente = Oferente.objects.create(
            usuario=cls.empresa, nombre_empresa='ZX Empresa reservada', cuit='30-12345678-1',
            logo='empresas/logos/logo-reservado.webp',
            estado_validacion=Oferente.EstadoValidacion.APROBADO,
            contacto_nombre='Responsable de prueba',
            contacto_cargo='RRHH', correo_publico='rrhh@example.com',
        )
        cls.usuario = Usuario.objects.create_user(email='postulante-confidencial@example.invalid')
        Postulante.objects.create(usuario=cls.usuario)
        cls.datos = {
            'empresa': cls.empresa,
            'categoria': Categoria.objects.create(nombre='Tecnología'),
            'nombre_puesto': 'Desarrollo web',
            'ubicacion': 'Resistencia',
            'descripcion': 'Desarrollar aplicaciones y mantener documentación.',
            'habilidades_duras': 'Python',
            'estado': 'activa',
            'fecha_cierre': timezone.now() + timedelta(days=15),
        }
        cls.confidencial = Oferta.objects.create(
            **cls.datos, titulo='Puesto reservado', es_confidencial=True,
        )

    def assert_empresa_oculta(self, response):
        self.assertContains(response, self.confidencial.titulo)
        self.assertContains(response, 'Empresa confidencial')
        self.assertNotContains(response, self.oferente.nombre_empresa)
        self.assertNotContains(response, self.oferente.logo.url)
        self.assertNotContains(response, reverse('perfil_oferente', args=[self.oferente.pk]))
        self.assertNotRegex(response.content.decode(), r'>\s*ZX\s*<')

    def test_busqueda_por_habilidad_conserva_oferta_sin_identificar_empresa(self):
        url = reverse('buscar_empleo')
        self.assert_empresa_oculta(self.client.get(url, {'q': 'Python'}))
        self.assertNotContains(self.client.get(url, {'q': 'ZX'}), self.confidencial.titulo)

    def test_favoritos_conserva_oferta_sin_identificar_empresa(self):
        self.client.force_login(self.usuario)
        guardado = self.client.post(reverse('alternar_favorita', args=[self.confidencial.pk]))
        self.assertEqual(guardado.json(), {'success': True, 'favorita': True})
        respuesta = self.client.get(reverse('favoritos'))
        self.assert_empresa_oculta(respuesta)
        self.assertContains(respuesta, reverse('detalle_oferta', args=[self.confidencial.pk]))

    def test_perfil_de_empresa_solo_lista_ofertas_activas_no_confidenciales(self):
        normal = Oferta.objects.create(**self.datos, titulo='Puesto visible')
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('perfil_oferente', args=[self.oferente.pk]))
        self.assertContains(respuesta, normal.titulo)
        self.assertContains(respuesta, self.oferente.nombre_empresa)
        self.assertNotContains(respuesta, self.confidencial.titulo)
        self.assertNotContains(respuesta, reverse('detalle_oferta', args=[self.confidencial.pk]))
        busqueda = self.client.get(reverse('buscar_empleo'), {'q': 'ZX'})
        self.assertContains(busqueda, normal.titulo)
        self.assertContains(busqueda, self.oferente.nombre_empresa)
        self.assertNotContains(busqueda, self.confidencial.titulo)

    def test_inicio_y_detalle_ocultan_empresa_pero_el_panel_propio_conserva_la_oferta(self):
        self.assert_empresa_oculta(self.client.get(reverse('home')))
        self.assert_empresa_oculta(self.client.get(reverse('detalle_oferta', args=[self.confidencial.pk])))
        self.client.force_login(self.empresa)
        self.assertContains(self.client.get(reverse('dashboard_empresa')), self.confidencial.titulo)
