from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from ofertas.models import Oferta
from usuarios.models import Oferente, Usuario
from ia.models import TrabajoExtraccion


class InstituteOfferReviewsTests(TestCase):
    def setUp(self):
        self.staff = Usuario.objects.create_user(email='institute@example.com', is_staff=True)
        self.owner = Usuario.objects.create_user(email='company@example.com')
        Oferente.objects.create(usuario=self.owner, nombre_empresa='Empresa habilitada', cuit='30123456781', estado_validacion='aprobado', contacto_nombre='Alex', contacto_cargo='RRHH', correo_publico='rrhh@example.com')
        category = Categoria.objects.create(nombre='Tecnología')
        self.data = {
            'titulo': 'Analista Python', 'nombre_puesto': 'Analista', 'categoria': category.pk,
            'ubicacion': 'Resistencia', 'modalidad': 'remoto', 'descripcion': 'Análisis de datos con Python.',
            'requisitos_obligatorios': 'Python', 'requisitos_deseables': '',
            'categorias_requisitos': '{"mandatory":["technical_skills"],"desirable":[]}',
            'experiencia_requerida': 'sin-experiencia', 'experiencia_clasificacion': 'no_solicitado',
            'educacion_clasificacion': 'no_solicitado',
            'fecha_cierre': (timezone.localdate() + timedelta(days=10)).isoformat(),
        }

    def submit_offer(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('crear_oferta'), self.data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTrue(response.json()['success'], response.json())
        return Oferta.objects.get(empresa=self.owner)

    def test_offer_waits_for_institute_approval_then_becomes_public(self):
        offer = self.submit_offer()
        self.assertEqual(offer.estado, 'pendiente')
        self.assertFalse(TrabajoExtraccion.objects.filter(oferta=offer).exists())
        self.assertEqual(self.client.get(reverse('detalle_oferta', args=[offer.pk])).status_code, 404)
        self.client.force_login(self.staff)
        notifications = self.client.get(reverse('mod_notificaciones_admin')).json()
        self.assertEqual(notifications['ofertas_pendientes'], 1)
        self.assertEqual(notifications['pendientes'], 1)
        self.assertEqual(notifications['recientes'][0]['url'], reverse('mod_detalle_oferta', args=[offer.pk]))
        listing = self.client.get(reverse('mod_listar_ofertas'))
        self.assertContains(listing, reverse('mod_aprobar_oferta', args=[offer.pk]))
        self.assertContains(listing, 'data-admin-notification-dot')
        detail = self.client.get(reverse('mod_detalle_oferta', args=[offer.pk]))
        self.assertContains(detail, 'Aprobar oferta')
        self.assertContains(detail, 'Rechazar oferta')
        self.client.post(reverse('mod_aprobar_oferta', args=[offer.pk]))
        offer.refresh_from_db()
        self.assertEqual(offer.estado, 'activa')
        self.assertTrue(TrabajoExtraccion.objects.filter(oferta=offer).exists())
        self.assertEqual(self.client.get(reverse('mod_notificaciones_admin')).json()['pendientes'], 0)
        self.assertEqual(self.client.get(reverse('detalle_oferta', args=[offer.pk])).status_code, 200)

    def test_rejecting_offer_clears_pending_alert_and_keeps_offer_private(self):
        offer = self.submit_offer()
        self.client.force_login(self.staff)
        response = self.client.post(reverse('mod_rechazar_oferta', args=[offer.pk]), {'motivo': 'Completá las tareas del puesto.'})
        self.assertEqual(response.status_code, 302)
        offer.refresh_from_db()
        self.assertEqual(offer.estado, 'rechazada')
        self.assertEqual(self.client.get(reverse('mod_notificaciones_admin')).json()['ofertas_pendientes'], 0)
        self.assertEqual(self.client.get(reverse('detalle_oferta', args=[offer.pk])).status_code, 404)
        self.assertFalse(TrabajoExtraccion.objects.filter(oferta=offer).exists())

    def test_company_and_offer_alerts_are_combined_and_private(self):
        self.submit_offer()
        new_owner = Usuario.objects.create_user(email='new-company@example.com')
        Oferente.objects.create(usuario=new_owner, nombre_empresa='Nueva empresa', cuit='30123456781')
        url = reverse('mod_notificaciones_admin')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.staff)
        response = self.client.get(url)
        self.assertEqual(response['Cache-Control'], 'no-store')
        data = response.json()
        self.assertEqual((data['empresas_pendientes'], data['ofertas_pendientes'], data['pendientes']), (1, 1, 2))
        self.assertEqual({item['tipo'] for item in data['recientes']}, {'Empresa', 'Oferta'})

    def test_non_staff_cannot_review_an_offer(self):
        offer = self.submit_offer()
        self.client.post(reverse('mod_aprobar_oferta', args=[offer.pk]))
        self.client.post(reverse('mod_rechazar_oferta', args=[offer.pk]), {'motivo': 'No permitido'})
        offer.refresh_from_db()
        self.assertEqual(offer.estado, 'pendiente')
