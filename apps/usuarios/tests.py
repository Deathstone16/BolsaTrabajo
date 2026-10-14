from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.test import TestCase
from django.urls import reverse

from .forms import CuitField, RegistroOferenteForm
from .validators import normalizar_cuit, validar_cuit


class CuitFieldTests(SimpleTestCase):
    def test_acepta_once_digitos_con_o_sin_guiones(self):
        campo = CuitField()
        self.assertEqual(campo.clean('30123456789'), '30123456789')
        self.assertEqual(campo.clean('30-12345678-9'), '30-12345678-9')

    def test_rechaza_letras(self):
        with self.assertRaises(ValidationError):
            CuitField().clean('30-ABC45678-9')


class RegistroOferenteTests(TestCase):
    def test_registro_carga_filtro_de_cuit(self):
        response = self.client.get(reverse('registro') + '?tipo=oferente')

        self.assertContains(response, 'data-cuit-input')
        self.assertContains(response, 'cuit-input.js')
class CuitValidatorTests(TestCase):
    def test_acepta_cuit_valido_con_o_sin_guiones(self):
        for cuit in ('20-12345678-6', '20123456786'):
            validar_cuit(cuit)

    def test_rechaza_cuit_con_digito_verificador_incorrecto(self):
        with self.assertRaises(ValidationError):
            validar_cuit('20-12345678-7')

    def test_rechaza_cuit_con_longitud_incorrecta(self):
        with self.assertRaises(ValidationError):
            validar_cuit('20-1234-6')

    def test_rechaza_letras_y_prefijos_invalidos(self):
        for cuit in ('20-ABC12345678-6', '99-12345678-4'):
            with self.assertRaises(ValidationError):
                validar_cuit(cuit)

    def test_registro_normaliza_el_cuit(self):
        form = RegistroOferenteForm(data={
            'nombre_empresa': 'Empresa de prueba',
            'cuit': '20123456786',
            'email': 'empresa-cuit@example.com',
            'password1': 'Clave-segura-123!',
            'password2': 'Clave-segura-123!',
        })

        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertEqual(form.cleaned_data['cuit'], '20-12345678-6')
        self.assertEqual(normalizar_cuit('20123456786'), '20-12345678-6')
