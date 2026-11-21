from unittest import skipUnless
from html.parser import HTMLParser
from io import BytesIO

from django.conf import settings
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader

from .views import TEMPLATES
from ientrabajo.ui_review import COMPANY_PREVIEWS


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href' and value and value.startswith('/'):
                    self.urls.add(value)


@skipUnless(getattr(settings, 'FRONTEND_DEMO', False), 'Only run with the isolated demo settings')
@override_settings(ALLOWED_HOSTS=['testserver'])
class DesignDemoTests(SimpleTestCase):
    # SimpleTestCase rejects every DB query: fixtures must render without tables.
    def test_every_demo_screen_renders_without_database_or_login(self):
        for screen_id in [*TEMPLATES, *COMPANY_PREVIEWS]:
            with self.subTest(screen_id=screen_id):
                response = self.client.get(reverse('design_demo_screen', args=[screen_id]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, screen_id)
                self.assertContains(response, 'Datos ficticios')

    def test_candidate_has_full_cv_profile_analysis_and_match(self):
        for screen_id, expected in [('POS-01', 'CV_Lucia_Gomez_DEMO.pdf'), ('POS-02', 'Tablero comercial'), ('POS-03', 'Analista de datos'), ('POS-04', 'Python'), ('POS-05', 'Excel'), ('POS-06', 'Lucía'), ('POS-08', 'Norte Digital'), ('POS-09', '82%')]:
            self.assertContains(self.client.get('/demo/' + screen_id + '/'), expected)

    def test_cv_states_remain_deterministic(self):
        for state in ('sin-cv', 'pendiente', 'error', 'completado'):
            self.assertContains(self.client.get('/demo/POS-01/', {'estado': state}), f'data-cv-state="{state}"')

    def test_writes_integrations_and_admin_are_unavailable(self):
        for url in ('/usuarios/registro/', '/usuarios/login/', '/ofertas/crear/', '/ofertas/editar-perfil/', '/ofertas/eliminar/1/', '/ia/solicitar-analisis/', '/demo/POS-06/'):
            self.assertEqual(self.client.post(url, {'email': 'test@example.com'}).status_code, 405)
        for url in ('/admin/', '/moderacion/', '/ws/cv/', '/ia/analisis/0/estado/', '/media/postulantes/cv/private.pdf'):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_internal_navigation_stays_available_without_records(self):
        links = Links()
        for screen_id in [*TEMPLATES, *COMPANY_PREVIEWS]:
            links.feed(self.client.get('/demo/' + screen_id + '/').content.decode())
        for link in links.urls:
            with self.subTest(link=link):
                self.assertEqual(self.client.get(link).status_code, 200)

    def test_demo_pdf_contains_only_synthetic_cv(self):
        response = self.client.get('/demo-cv/')
        self.assertEqual(response['Content-Type'], 'application/pdf')
        text = PdfReader(BytesIO(response.content)).pages[0].extract_text()
        self.assertIn('DATOS FICTICIOS', text)
        self.assertIn('lucia.demo@example.com', text)

    def test_static_assets_work_with_debug_off_and_filters_use_fixtures(self):
        self.assertFalse(settings.DEBUG)
        self.assertEqual(self.client.get('/static/css/ui/ien-theme.css').status_code, 200)
        response = self.client.get('/cursos/', {'q': 'Python'})
        self.assertContains(response, 'Python desde cero')
        self.assertNotContains(response, '>Excel para el trabajo<')
        self.assertEqual(self.client.get('/cursos/1/').context['curso'].pk, 1)
        self.assertEqual(self.client.get('/ofertas/2/').context['oferta'].pk, 2)
        self.assertEqual(self.client.get('/health/').status_code, 200)
