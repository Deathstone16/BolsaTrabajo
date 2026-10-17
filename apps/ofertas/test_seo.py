import re
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from ofertas.models import Oferta
from usuarios.models import Usuario


class PublicPageSEOTests(TestCase):
    def test_home_and_search_have_distinct_descriptions_and_ordered_headings(self):
        home = self.client.get(reverse('home')).content.decode()
        search = self.client.get(reverse('buscar_empleo')).content.decode()

        self.assertIn('Buscá ofertas de trabajo en el nordeste argentino', home)
        self.assertIn('Explorá ofertas laborales activas en IEN Empleo', search)
        for html in (home, search):
            headings = [int(level) for level in re.findall(r'<h([1-6])(?:\s|>)', html)]
            self.assertEqual(headings.count(1), 1)
            self.assertEqual(headings[0], 1)
            self.assertTrue(all(current <= previous + 1 for previous, current in zip(headings, headings[1:])))


@override_settings(DEBUG=True)
class DemoOffersCommandTests(TestCase):
    def test_command_creates_realistic_demo_offers_once(self):
        call_command('seed_seo_offers', stdout=StringIO())
        self.assertEqual(Oferta.objects.count(), 4)
        self.assertEqual(Oferta.objects.filter(estado='activa').count(), 4)
        self.assertContains(self.client.get(reverse('buscar_empleo')), 'Analista de datos junior')
        self.assertContains(self.client.get(reverse('home')), 'Representante de atención al cliente')
        detail = self.client.get(reverse('detalle_oferta', args=[Oferta.objects.first().pk])).content.decode()
        headings = [int(level) for level in re.findall(r'<h([1-6])(?:\s|>)', detail)]
        self.assertEqual(headings.count(1), 1)
        self.assertTrue(all(current <= previous + 1 for previous, current in zip(headings, headings[1:])))
        user = Usuario.objects.get(email='litoral-soluciones@seo-demo.invalid')
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())

        call_command('seed_seo_offers', stdout=StringIO())
        self.assertEqual(Oferta.objects.count(), 4)

    @override_settings(DEBUG=False)
    def test_command_refuses_production(self):
        with self.assertRaises(CommandError):
            call_command('seed_seo_offers', stdout=StringIO())
