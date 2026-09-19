from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from usuarios.models import Oferente, Usuario

from .forms import OfertaForm
from .models import Oferta


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
        data = {**self.data, "habilidades_duras": ""}
        form = OfertaForm(data)

        self.assertFalse(form.is_valid())
        self.assertIn("habilidades_duras", form.errors)

    def test_rechaza_habilidad_repetida_ignorando_mayusculas(self):
        data = {**self.data, "habilidades_duras": "Python, python"}
        form = OfertaForm(data)

        self.assertFalse(form.is_valid())
        self.assertIn("habilidades_duras", form.errors)

    def test_rechaza_habilidad_presente_en_ambas_secciones(self):
        data = {**self.data, "habilidades_blandas": "PYTHON"}
        form = OfertaForm(data)

        self.assertFalse(form.is_valid())
        self.assertIn("habilidades_blandas", form.errors)

    def test_save_combina_habilidades_en_campo_heredado(self):
        form = OfertaForm(self.data)
        self.assertTrue(form.is_valid(), form.errors.as_json())

        oferta = form.save(commit=False)

        self.assertEqual(
            oferta.habilidades_requeridas,
            "Python, Django, Comunicación, Trabajo en equipo",
        )

    def test_crear_oferta_ajax_y_recuperar_datos_para_edicion(self):
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse("crear_oferta"),
            self.data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        oferta = Oferta.objects.get(pk=response.json()["id"])
        self.assertEqual(oferta.habilidades_duras, "Python, Django")
        self.assertEqual(oferta.habilidades_blandas, "Comunicación, Trabajo en equipo")
        self.assertEqual(
            oferta.habilidades_requeridas,
            "Python, Django, Comunicación, Trabajo en equipo",
        )

        response = self.client.get(reverse("datos_oferta", args=[oferta.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["habilidades_duras"], ["Python", "Django"])
        self.assertEqual(
            response.json()["habilidades_blandas"],
            ["Comunicación", "Trabajo en equipo"],
        )
