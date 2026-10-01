from django.forms import ValidationError
from django.test import SimpleTestCase
from django.test import TestCase
from django.urls import reverse

from .forms import CuitField


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
