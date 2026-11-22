from django.test import TestCase
from django.urls import reverse

from categorias.models import Categoria, Habilidad
from usuarios.models import Usuario


class GestionHabilidadesTests(TestCase):
    def setUp(self):
        self.staff = Usuario.objects.create_user(email='staff-skills@example.com', is_staff=True)
        self.categoria = Categoria.objects.create(nombre='Tecnología')
        self.otra = Categoria.objects.create(nombre='Administración')
        self.client.force_login(self.staff)

    def test_categoria_tiene_acceso_a_crear_y_gestionar_habilidades(self):
        lista = self.client.get(reverse('mod_listar_categorias'))
        self.assertContains(lista, reverse('mod_listar_habilidades', args=[self.categoria.pk]))
        self.assertEqual(lista.context['categorias'].get(pk=self.categoria.pk).total_habilidades, 0)
        editar = self.client.get(reverse('mod_modificar_categoria', args=[self.categoria.pk]))
        self.assertContains(editar, reverse('mod_crear_habilidad', args=[self.categoria.pk]))

    def test_crear_listar_y_editar_nombre_y_tipo_sin_cambiar_categoria(self):
        crear = reverse('mod_crear_habilidad', args=[self.categoria.pk])
        self.assertContains(self.client.get(crear), 'name="tipo_habilidad"')
        respuesta = self.client.post(crear, {'nombre': 'Python', 'tipo_habilidad': 'D'})
        lista = reverse('mod_listar_habilidades', args=[self.categoria.pk])
        self.assertRedirects(respuesta, lista)
        habilidad = Habilidad.objects.get(nombre='Python')
        self.assertEqual(habilidad.categoria, self.categoria)
        self.assertEqual(habilidad.tipo_habilidad, 'D')
        editar = reverse('mod_modificar_habilidad', args=[habilidad.pk])
        self.assertContains(self.client.get(lista), editar)
        self.assertContains(self.client.get(lista), 'Habilidad técnica')
        respuesta = self.client.post(editar, {
            'nombre': 'Comunicación', 'tipo_habilidad': 'B', 'categoria': self.otra.pk,
        })
        self.assertRedirects(respuesta, lista)
        habilidad.refresh_from_db()
        self.assertEqual(habilidad.nombre, 'Comunicación')
        self.assertEqual(habilidad.tipo_habilidad, 'B')
        self.assertEqual(habilidad.categoria, self.categoria)
        self.assertContains(self.client.get(lista), 'Habilidad blanda')
        self.assertNotContains(self.client.get(reverse('mod_listar_habilidades', args=[self.otra.pk])), habilidad.nombre)

    def test_no_duplica_nombres_en_categoria_pero_permite_otra_categoria(self):
        Habilidad.objects.create(categoria=self.categoria, nombre='Python', tipo_habilidad='D')
        crear = reverse('mod_crear_habilidad', args=[self.categoria.pk])
        respuesta = self.client.post(crear, {'nombre': 'python', 'tipo_habilidad': 'D'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('nombre', respuesta.context['form'].errors)
        respuesta = self.client.post(reverse('mod_crear_habilidad', args=[self.otra.pk]), {
            'nombre': 'Python', 'tipo_habilidad': 'D',
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Habilidad.objects.filter(nombre__iexact='Python').count(), 2)

    def test_usuario_sin_staff_no_puede_modificar_catalogo(self):
        habilidad = Habilidad.objects.create(categoria=self.categoria, nombre='Excel', tipo_habilidad='D')
        self.client.force_login(Usuario.objects.create_user(email='no-staff@example.com'))
        for url in (reverse('mod_crear_habilidad', args=[self.categoria.pk]),
                    reverse('mod_modificar_habilidad', args=[habilidad.pk])):
            self.assertNotEqual(self.client.post(url, {'nombre': 'Otro', 'tipo_habilidad': 'B'}).status_code, 200)
        habilidad.refresh_from_db()
        self.assertEqual(habilidad.nombre, 'Excel')
