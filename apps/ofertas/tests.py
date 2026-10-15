from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from usuarios.models import Oferente, Usuario

from .forms import OfertaForm
from .models import Oferta
from .models import OfertaFavorita
from usuarios.models import Postulante


class OfertaFormTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Tecnología")
        self.usuario = Usuario.objects.create_user(
            email="empresa@example.com",
            password="test-password",
        )
        Oferente.objects.create(
            usuario=self.usuario,
            estado_validacion=Oferente.EstadoValidacion.APROBADO,
            nombre_empresa="Empresa de prueba",
            cuit="30-12345678-9",
        )
        self.data = {
            "titulo": "Desarrollador backend",
            "nombre_puesto": "Backend Developer",
            "categoria": self.categoria.pk,
            "ubicacion": "Córdoba",
            "modalidad": "remoto",
            "descripcion": "Desarrollo y mantenimiento de aplicaciones web.",
            "habilidades_duras": "Python, Django",
            "habilidades_blandas": "Comunicación, Trabajo en equipo",
            "experiencia_requerida": "1-2",
            "nivel_educativo": "universitario",
            "fecha_cierre": (timezone.localdate() + timedelta(days=7)).isoformat(),
        }

    def test_formulario_valido_no_exige_campo_heredado(self):
        form = OfertaForm(self.data)
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_exige_al_menos_una_habilidad_dura(self):
        form = OfertaForm({**self.data, "habilidades_duras": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("habilidades_duras", form.errors)

    def test_rechaza_repeticiones_en_y_entre_secciones(self):
        repetida = OfertaForm({**self.data, "habilidades_duras": "Python, python"})
        cruzada = OfertaForm({**self.data, "habilidades_blandas": "PYTHON"})
        self.assertIn("habilidades_duras", repetida.errors)
        self.assertIn("habilidades_blandas", cruzada.errors)

    def test_paginas_de_formulario_muestran_ambas_secciones_de_habilidades(self):
        self.client.force_login(self.usuario)
        oferta = Oferta.objects.create(
            empresa=self.usuario,
            categoria=self.categoria,
            titulo="Desarrollador backend",
            nombre_puesto="Backend Developer",
            ubicacion="Córdoba",
            descripcion="Descripción de prueba",
            habilidades_requeridas="Python",
            habilidades_duras="Python",
            nivel_educativo="universitario",
            fecha_cierre=timezone.localdate() + timedelta(days=7),
        )
        crear = self.client.get(reverse("crear_oferta"))
        editar = self.client.get(reverse("editar_oferta", args=[oferta.pk]))
        for response in (crear, editar):
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'id="tags-input-duras"')
            self.assertContains(response, 'id="tags-input-blandas"')
    def test_crear_y_editar_oferta_con_habilidades_separadas(self):
        self.client.force_login(self.usuario)
        response = self.client.post(
            reverse("crear_oferta"),
            self.data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"], response.json())

        oferta = Oferta.objects.get(empresa=self.usuario)
        self.assertEqual(oferta.habilidades_duras, "Python, Django")
        self.assertEqual(oferta.habilidades_blandas, "Comunicación, Trabajo en equipo")
        self.assertEqual(
            oferta.habilidades_requeridas,
            "Python, Django, Comunicación, Trabajo en equipo",
        )

        editados = {
            **self.data,
            "habilidades_duras": "SQL",
            "habilidades_blandas": "Liderazgo",
        }
        response = self.client.post(
            reverse("editar_oferta", args=[oferta.pk]),
            editados,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"], response.json())
        oferta.refresh_from_db()
        self.assertEqual(oferta.habilidades_duras, "SQL")
        self.assertEqual(oferta.habilidades_blandas, "Liderazgo")
        self.assertEqual(oferta.habilidades_requeridas, "SQL, Liderazgo")
class EmpleosGuardadosTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(email='saved@example.com', password='test-password')
        self.candidate = Postulante.objects.create(usuario=self.user)
        company = Usuario.objects.create_user(email='saved-company@example.com', password='test-password')
        category = Categoria.objects.create(nombre='Pruebas favoritos')
        self.offer = Oferta.objects.create(
            empresa=company, categoria=category, titulo='Oferta guardable', nombre_puesto='Backend',
            ubicacion='Córdoba', descripcion='Oferta de prueba', habilidades_requeridas='Python',
            nivel_educativo='secundario', estado='activa', fecha_cierre=timezone.now() + timedelta(days=5),
        )
        self.toggle = reverse('alternar_favorita', args=[self.offer.pk])
        self.client.force_login(self.user)

    def test_guardar_listar_y_quitar_oferta(self):
        self.assertTrue(self.client.post(self.toggle).json()['favorita'])
        self.assertContains(self.client.get(reverse('favoritos')), self.offer.titulo)
        detail = self.client.get(reverse('detalle_oferta', args=[self.offer.pk]))
        self.assertContains(detail, 'data-save-on="true"')
        self.assertContains(self.client.get(reverse('buscar_empleo')), self.offer.titulo)
        self.assertFalse(self.client.post(self.toggle).json()['favorita'])
        self.assertFalse(OfertaFavorita.objects.filter(postulante=self.candidate).exists())
        self.assertContains(self.client.get(reverse('favoritos')), 'Todavía no guardaste ofertas')

    def test_favoritos_son_privados_por_postulante(self):
        self.client.post(self.toggle)
        other = Usuario.objects.create_user(email='saved-other@example.com', password='test-password')
        Postulante.objects.create(usuario=other)
        self.client.force_login(other)
        self.assertNotContains(self.client.get(reverse('favoritos')), self.offer.titulo)

    def test_guardar_requiere_post_y_sesion(self):
        self.assertEqual(self.client.get(self.toggle).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(self.toggle).status_code, 302)
        self.assertFalse(OfertaFavorita.objects.exists())

    def test_oferta_inexistente_devuelve_404(self):
        self.assertEqual(self.client.post(reverse('alternar_favorita', args=[999999])).status_code, 404)

    def test_oferta_finalizada_se_conserva_y_puede_quitarse(self):
        self.client.post(self.toggle)
        self.offer.estado = 'finalizada'
        self.offer.save()
        page = self.client.get(reverse('favoritos'))
        self.assertContains(page, 'Esta oferta ya no está disponible')
        self.assertFalse(self.client.post(self.toggle).json()['favorita'])

    def test_proteccion_csrf_en_guardado(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(reverse('detalle_oferta', args=[self.offer.pk]))
        self.assertEqual(client.post(self.toggle).status_code, 403)
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post(self.toggle, HTTP_X_CSRFTOKEN=token).status_code, 200)
