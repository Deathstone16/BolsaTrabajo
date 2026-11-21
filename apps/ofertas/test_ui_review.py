from django.test import TestCase, override_settings
from django.urls import reverse

from ientrabajo.ui_review import SCREENS, COMPANY_PREVIEWS
from usuarios.models import Usuario, Oferente
from ofertas.models import Oferta
from categorias.models import Categoria
from django.utils import timezone
from datetime import timedelta


@override_settings(DEBUG=True)
class ScreenReviewTests(TestCase):
    def test_index_and_ids_are_unique(self):
        self.assertEqual(len({screen.id for screen in SCREENS}), len(SCREENS))
        response = self.client.get(reverse('ui_review'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mapa de pantallas')
        self.assertContains(response, 'ADM-01')
        admin_group = next(g for g in response.context['screen_groups'] if g['title'] == 'Administración')
        self.assertTrue(all(not item['url'] for item in admin_group['items']))

    def test_marker_distinguishes_registration_variants(self):
        candidate = self.client.get(reverse('registro'))
        company = self.client.get(reverse('registro') + '?tipo=oferente')
        self.assertEqual(candidate.context['ui_review_screen'].id, 'ACC-02')
        self.assertEqual(company.context['ui_review_screen'].id, 'EMP-01')
        self.assertContains(company, 'ien-screen-marker')

    @override_settings(DEBUG=False)
    def test_map_and_markers_are_absent_in_production(self):
        self.assertEqual(self.client.get(reverse('ui_review')).status_code, 404)
        self.assertNotContains(self.client.get(reverse('login')), 'class="ien-screen-marker"')

    def test_employer_links_use_only_own_offer_and_current_status(self):
        owner = Usuario.objects.create_user(email='review@example.com')
        Oferente.objects.create(usuario=owner, nombre_empresa='Review', cuit='30123456781', estado_validacion='aprobado', contacto_nombre='Responsable', contacto_cargo='RRHH', correo_publico='rrhh@example.com')
        other = Usuario.objects.create_user(email='other-review@example.com')
        category = Categoria.objects.create(nombre='Review')
        def offer(user):
            return Oferta.objects.create(empresa=user, categoria=category, titulo='Review', nombre_puesto='Review', ubicacion='Chaco', descripcion='Review', fecha_cierre=timezone.now() + timedelta(days=5))
        foreign = offer(other)
        own = offer(owner)
        self.client.force_login(owner)
        response = self.client.get(reverse('ui_review'))
        items = {item['screen'].id: item for group in response.context['screen_groups'] for item in group['items']}
        self.assertEqual(items['EMP-09']['url'], reverse('editar_oferta', args=[own.pk]))
        self.assertNotEqual(items['EMP-09']['url'], reverse('editar_oferta', args=[foreign.pk]))
        self.assertFalse(items['EMP-03']['url'])
        self.assertTrue(items['EMP-04']['url'])
        self.assertFalse(items['EMP-05']['url'])
        status = self.client.get(reverse('validacion_pendiente'))
        self.assertEqual(status.context['ui_review_screen'].id, 'EMP-04')

    def test_index_rejects_posts(self):
        self.assertEqual(self.client.post(reverse('ui_review')).status_code, 405)

    def test_company_previews_work_without_account_or_database_fixtures(self):
        for screen_id in COMPANY_PREVIEWS:
            with self.subTest(screen_id=screen_id):
                url = reverse('ui_review_company', args=[screen_id])
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['ui_review_screen'].id, screen_id)
                self.assertContains(response, 'Datos ficticios')
                self.assertEqual(response['Content-Security-Policy'], "form-action 'none'; connect-src 'none'")
                self.assertEqual(self.client.post(url, {'nombre_empresa': 'Cambio'}).status_code, 405)
        self.assertEqual(Usuario.objects.count(), 0)
        self.assertEqual(Oferente.objects.count(), 0)
        self.assertEqual(Oferta.objects.count(), 0)

    def test_company_preview_navigation_and_forms_stay_in_preview(self):
        response = self.client.get(reverse('ui_review_company', args=['EMP-06']))
        self.assertContains(response, 'href="' + reverse('ui_review_company', args=['EMP-09']) + '"')
        self.assertContains(response, 'action="' + reverse('ui_review_company', args=['EMP-06']) + '"')
        self.assertNotContains(response, 'action="' + reverse('editar_perfil_empresa') + '"')
        items = [item for group in self.client.get(reverse('ui_review')).context['screen_groups'] for item in group['items']]
        self.assertTrue(all(item['preview_url'] for item in items if item['screen'].id in COMPANY_PREVIEWS))

    @override_settings(DEBUG=False)
    def test_company_previews_are_unavailable_in_production(self):
        for screen_id in COMPANY_PREVIEWS:
            self.assertEqual(self.client.get(reverse('ui_review_company', args=[screen_id])).status_code, 404)

    def test_unknown_company_preview_is_not_found(self):
        self.assertEqual(self.client.get(reverse('ui_review_company', args=['ADM-01'])).status_code, 404)
