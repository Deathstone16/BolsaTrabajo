from django.test import TestCase
from django.urls import reverse

from usuarios.forms import OferenteForm
from usuarios.models import Oferente, Postulante, Usuario


class ContactoEmpresaTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(email='contacto@example.com')
        self.oferente = Oferente.objects.create(
            usuario=self.usuario, nombre_empresa='Empresa de prueba', cuit='30-12345678-1',
            estado_validacion=Oferente.EstadoValidacion.APROBADO,
        )
        self.datos = {'nombre_empresa': self.oferente.nombre_empresa, 'cuit': self.oferente.cuit}
        self.client.force_login(self.usuario)

    def login_postulante(self):
        usuario = Usuario.objects.create_user(email='postulante-contacto@example.com')
        Postulante.objects.create(usuario=usuario)
        self.client.force_login(usuario)

    def test_responsible_name_is_required_and_old_empty_profiles_still_render(self):
        form = OferenteForm(self.datos, instance=self.oferente)
        self.assertFalse(form.is_valid())
        self.assertIn('contacto_nombre', form.errors)
        self.assertNotIn('contacto_email', form.fields)
        self.assertNotIn('contacto_telefono', form.fields)
        self.login_postulante()
        response = self.client.get(reverse('perfil_oferente', args=[self.oferente.pk]))
        self.assertNotContains(response, 'aria-label="Contacto de la empresa"')

    def test_responsible_name_saves_without_personal_email_or_phone(self):
        response = self.client.post(reverse('editar_perfil_empresa'), {
            **self.datos, 'contacto_nombre': 'María Pérez', 'contacto_cargo': 'RRHH',
        })
        self.assertRedirects(response, reverse('dashboard_empresa') + '#empresa')
        self.oferente.refresh_from_db()
        self.assertEqual(self.oferente.contacto_nombre, 'María Pérez')
        self.login_postulante()
        response = self.client.get(reverse('perfil_oferente', args=[self.oferente.pk]))
        self.assertContains(response, 'María Pérez')
        self.assertContains(response, 'RRHH')
        self.assertNotContains(response, 'mailto:')

    def test_role_is_optional_and_whitespace_name_is_rejected(self):
        form = OferenteForm({**self.datos, 'contacto_nombre': 'María Pérez'}, instance=self.oferente)
        self.assertTrue(form.is_valid(), form.errors)
        form = OferenteForm({**self.datos, 'contacto_nombre': '   '}, instance=self.oferente)
        self.assertFalse(form.is_valid())
        self.assertIn('contacto_nombre', form.errors)
