from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Curso


class CourseOfficialLinkTests(TestCase):
    def setUp(self):
        self.course = Curso.objects.create(
            nombre='Curso de prueba', categoria=Categoria.objects.create(nombre='Tecnología'),
            descripcion='Descripción de prueba', duracion='8 semanas', horario='Martes 18 h',
        )

    def test_links_to_exact_course_page_in_a_new_tab(self):
        self.course.url_externa = 'https://ien.edu.ar/cursos/curso-de-prueba/'
        self.course.save(update_fields=['url_externa'])
        response = self.client.get(reverse('cursos:detalle', args=[self.course.pk]))
        self.assertContains(response, f'href="{self.course.url_externa}" target="_blank" rel="noopener noreferrer"')
        self.assertContains(response, 'Ver curso en el IEN')
        self.assertNotContains(response, 'El enlace oficial de este curso todavía no fue cargado.')

    def test_without_official_url_does_not_invent_a_destination(self):
        response = self.client.get(reverse('cursos:detalle', args=[self.course.pk]))
        self.assertContains(response, 'disabled aria-describedby="curso-enlace-ayuda"')
        self.assertContains(response, 'El enlace oficial de este curso todavía no fue cargado.')
        self.assertNotContains(response, 'href="https://ien.edu.ar/cursos/')
