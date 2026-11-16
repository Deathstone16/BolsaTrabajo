import tempfile
from io import BytesIO

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.models import Oferente, Usuario


class FotoPerfilOferenteTests(TestCase):
    def test_photo_upload_is_saved_and_displayed_in_company_panel(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            usuario = Usuario.objects.create_user(email='foto@example.com')
            oferente = Oferente.objects.create(
                usuario=usuario, nombre_empresa='Empresa de prueba', cuit='30-12345678-1',
                estado_validacion=Oferente.EstadoValidacion.APROBADO,
            )
            self.client.force_login(usuario)
            panel = self.client.get(reverse('dashboard_empresa'))
            self.assertNotContains(panel, 'Agregar foto')
            self.assertNotContains(panel, 'name="logo"')
            image = BytesIO()
            Image.new('RGB', (64, 64), 'blue').save(image, format='PNG')
            response = self.client.post(reverse('editar_perfil_empresa'), {
                'nombre_empresa': oferente.nombre_empresa, 'cuit': oferente.cuit,
                'contacto_nombre': 'María Pérez',
                'logo': SimpleUploadedFile('foto.png', image.getvalue(), content_type='image/png'),
                'banner': SimpleUploadedFile('portada.png', image.getvalue(), content_type='image/png'),
                'sitio_web': 'https://example.com',
            })
            self.assertRedirects(response, reverse('dashboard_empresa') + '#empresa')
            oferente.refresh_from_db()
            self.assertTrue(oferente.logo.storage.exists(oferente.logo.name))
            self.assertTrue(oferente.banner.storage.exists(oferente.banner.name))
            panel = self.client.get(reverse('dashboard_empresa'))
            self.assertContains(panel, oferente.logo.url)
            self.assertContains(panel, oferente.banner.url)
            self.assertContains(panel, 'btn-ghost ien-company-website')
            self.assertNotContains(panel, 'Cambiar foto')
            edit = self.client.get(reverse('editar_perfil_empresa'))
            self.assertContains(edit, 'Foto de perfil o logo')
            self.assertContains(edit, 'data-photo-preview')
            self.assertContains(edit, 'data-cover-background')
            self.assertContains(edit, 'data-photo-zoom')
            self.assertContains(edit, 'name="banner"')
            self.assertContains(edit, 'js/profile-photo.js')
