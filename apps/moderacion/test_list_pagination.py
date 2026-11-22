from django.test import TestCase
from django.urls import reverse

from categorias.models import Categoria, Habilidad
from cursos.models import Curso
from usuarios.models import Oferente, Usuario


class AdminListPaginationTests(TestCase):
    def setUp(self):
        self.client.force_login(Usuario.objects.create_user(email='paging-admin@example.com', is_staff=True))
        self.category = Categoria.objects.create(nombre='Catálogo')

    def test_pending_company_precedes_newer_approved_companies(self):
        owner = Usuario.objects.create_user(email='pending-page@example.com')
        pending = Oferente.objects.create(usuario=owner, nombre_empresa='Pendiente antigua', cuit='30111111111', estado_validacion='pendiente')
        for n in range(11):
            owner = Usuario.objects.create_user(email=f'approved-page-{n}@example.com')
            Oferente.objects.create(usuario=owner, nombre_empresa=f'Empresa {n}', cuit=f'302222222{n:02d}', estado_validacion='aprobado')
        response = self.client.get(reverse('mod_listar_empresas'))
        self.assertEqual(response.context['empresas'][0].pk, pending.pk)
        self.assertEqual(len(response.context['empresas']), 10)
        self.assertEqual(response.context['total'], 1)
        self.assertContains(response, 'page=2')
        self.assertLess(response.content.index(b'Pendientes de validaci'), response.content.index(b'<table'))
        self.assertEqual(len(self.client.get(reverse('mod_listar_empresas'), {'page': 2}).context['empresas']), 2)
        filtered = self.client.get(reverse('mod_listar_empresas'), {'q': 'Pendiente antigua'})
        self.assertEqual(filtered.context['pagina'].paginator.count, 1)

    def test_courses_paginate_after_filtering_and_keep_global_count(self):
        for n in range(11):
            Curso.objects.create(nombre=f'Curso {n:02d}', categoria=self.category, descripcion='Descripción', duracion='8 semanas', horario='Lunes de 09:00 a 10:00')
        response = self.client.get(reverse('mod_listar_cursos'))
        self.assertEqual(len(response.context['cursos']), 9)
        self.assertEqual(response.context['total_cursos'], 11)
        response = self.client.get(reverse('mod_listar_cursos'), {'q': 'Curso 10', 'page': 2})
        self.assertEqual([course.nombre for course in response.context['cursos']], ['Curso 10'])

    def test_categories_and_skills_have_bounded_pages_and_back_links(self):
        for n in range(12):
            Categoria.objects.create(nombre=f'Categoría {n}')
            Habilidad.objects.create(nombre=f'Habilidad {n}', categoria=self.category)
        categories = self.client.get(reverse('mod_listar_categorias'))
        self.assertEqual(len(categories.context['categorias']), 10)
        skills = self.client.get(reverse('mod_listar_habilidades', args=[self.category.pk]))
        self.assertEqual(len(skills.context['habilidades']), 10)
        self.assertContains(skills, 'Volver a las categorías')
        self.assertContains(skills, f'href="{reverse("mod_listar_categorias")}"')
        self.assertEqual(self.client.get(reverse('mod_listar_habilidades', args=[self.category.pk]), {'page': 'bad'}).status_code, 200)
