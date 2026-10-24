from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from ia.models import AnalisisCV, CVVersion, EstadoPerfil, PerfilCV
from ia.templatetags.education_presentation import education_status, education_title
from usuarios.models import Postulante


class SectionTextParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.text = {
            "data-profile-courses": [], "data-profile-education": [], "data-profile-skills": [],
        }

    def handle_starttag(self, tag, attrs):
        active = set(self.stack[-1][1]) if self.stack else set()
        attributes = dict(attrs)
        for marker in self.text:
            if marker in attributes:
                active.add(marker)
        if tag not in self.VOID_TAGS:
            self.stack.append((tag, active))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        active = self.stack[-1][1] if self.stack else set()
        for marker in active:
            self.text[marker].append(data)


class EducationPresentationTests(TestCase):
    def test_legacy_entities_render_as_text_without_enabling_html(self):
        output = Template('{% load education_presentation %}{{ value|human_text }}').render(
            Context({'value': 'Comunicaci&oacute;n &lt;script&gt;alert(1)&lt;/script&gt;'}))
        self.assertIn('Comunicación', output)
        self.assertIn('&lt;script&gt;', output)
        self.assertNotIn('<script>', output)

    def test_cursado_licenciatura_does_not_claim_a_degree(self):
        study = {'level': 'bachelor', 'field': 'Lic. en Comunicación social',
                 'completed': None, 'completion_status': 'unknown',
                 'source_quotes': ['Lic. en Comunicación social', 'cursado 2016-2018 UNNE']}
        self.assertEqual(education_title(study), 'Licenciatura en Comunicación social')
        self.assertEqual(education_status(study), 'Cursado; título no informado')

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="education-presentation@example.invalid", password="synthetic-test-password",
        )
        self.postulante = Postulante.objects.create(usuario=self.user)
        self.cv_version = CVVersion.objects.create(
            postulante=self.postulante, numero=1, archivo="synthetic-cv.txt",
            nombre_original="synthetic-cv.txt", sha256="a" * 64, formato="txt", tamano=1,
        )
        self.postulante.cv_version_actual = self.cv_version
        self.postulante.save(update_fields=["cv_version_actual"])
        self.content = {
            "schema_version": "candidate-profile.v2",
            "summary": "Perfil sintético de prueba.",
            "skills": [
                {"name": "Python", "kind": "technical", "level": "intermediate", "evidence": ["Uso en proyectos"]},
            ],
            "projects": [{"name": "Sistema de turnos", "highlights": ["Creó el calendario de reservas"],
                          "source_quotes": ["Sistema de turnos"]}],
            "education": [
                {
                    "level": "bachelor", "field": "Informática", "institution": "Universidad Sintética",
                    "completed": True, "completion_status": "completed", "source_quotes": [],
                },
                {
                    "level": "doctorate", "field": "Informática", "institution": "Universidad Sintética",
                    "completed": False, "completion_status": "in_progress", "source_quotes": [],
                },
                {
                    "level": "master", "field": "Economía", "completed": False,
                    "completion_status": "unknown", "source_quotes": [],
                },
                {
                    "level": "technical", "field": "Diseño", "completed": None,
                    "completion_status": "incomplete", "source_quotes": [],
                },
                {"level": "other", "field": "", "source_quotes": []},
                {
                    "level": "other", "field": "Curso de Excel", "institution": "Instituto Sintético",
                    "completed": False, "completion_status": "in_progress", "source_quotes": [],
                },
            ],
            "credentials": [
                {
                    "name": "Certificación Excel", "issuer": "Instituto Sintético",
                    "issued_at": None, "expires_at": None, "evidence": ["Curso declarado"],
                    "source_quotes": [], "origin": "declared",
                },
            ],
        }
        self.profile = PerfilCV.objects.create(
            postulante=self.postulante, cv_version=self.cv_version, contenido=self.content,
            version=1, source_hash="b" * 64, schema_version="candidate-profile.v2",
            estado=EstadoPerfil.LISTO,
        )
        self.analysis = AnalisisCV.objects.create(
            postulante=self.postulante, version_cv=self.cv_version, perfil_snapshot=self.content,
            estado=AnalisisCV.Estado.COMPLETADO,
            respuesta={"result": {"resumen_ejecutivo": "Perfil sintético.", "habilidades_analizadas": []}},
        )
        self.client.force_login(self.user)

    def assert_only_academic_education_is_visible(self, response):
        self.assertContains(response, 'data-profile-education')
        self.assertEqual(len(self.content["education"]), 6)
        self.assertContains(response, "Doctorado en Informática")
        self.assertContains(response, "En curso")
        self.assertContains(response, "Grado universitario en Informática")
        self.assertContains(response, "Finalizado")
        self.assertContains(response, "Incompleto")
        self.assertContains(response, "Estado no informado")
        self.assertNotContains(response, "Doctor en Informática")
        self.assertNotContains(response, 'data-profile-courses')
        self.assertContains(response, 'data-profile-skills')
        parser = SectionTextParser()
        parser.feed(response.content.decode())
        self.assertNotIn("Curso de Excel", "".join(parser.text["data-profile-education"]))
        self.assertNotIn("Curso de Excel", "".join(parser.text["data-profile-skills"]))
        self.assertNotContains(response, "Certificación Excel")

    def test_resultado_muestra_estudios_sin_cursos_ni_credenciales(self):
        response = self.client.get(reverse("ia:ver_resultado", args=[self.analysis.pk]))
        self.assertEqual(response.status_code, 200)
        self.assert_only_academic_education_is_visible(response)
        self.assertContains(response, 'data-profile-projects')
        self.assertContains(response, 'Sistema de turnos')

    def test_perfil_presenta_estado_academico_sin_convertir_false_en_en_curso(self):
        response = self.client.get(reverse("mi_perfil"))
        self.assertEqual(response.status_code, 200)
        self.assert_only_academic_education_is_visible(response)
        self.assertContains(response, 'Sistema de turnos')
        self.assertContains(response, "No finalizado")

    def test_course_record_in_other_education_is_not_shown_as_study_or_skill(self):
        response = self.client.get(reverse("ia:ver_resultado", args=[self.analysis.pk]))
        self.assertEqual(response.status_code, 200)
        parser = SectionTextParser()
        parser.feed(response.content.decode())
        education_text = "".join(parser.text["data-profile-education"])
        skills_text = "".join(parser.text["data-profile-skills"])
        self.assertNotContains(response, 'data-profile-courses')
        self.assertNotIn("Curso de Excel", education_text)
        self.assertNotIn("Curso de Excel", skills_text)
        self.assertEqual(
            education_title({"level": "doctorate", "field": "Doctorado en Informática"}),
            "Doctorado en Informática",
        )
        self.assertEqual(
            education_title({"level": "bachelor", "field": "Informática"}),
            "Grado universitario en Informática",
        )

    def test_resultado_reconstruye_resumen_si_el_perfil_tiene_hechos_pero_no_resumen(self):
        self.analysis.perfil_snapshot = {
            **self.content, "summary": None,
            "work_experience": [{"job_title": "Desarrolladora", "organization": "Empresa"}],
        }
        self.analysis.respuesta = {"result": {"habilidades_analizadas": []}}
        self.analysis.save(update_fields=["perfil_snapshot", "respuesta"])

        response = self.client.get(reverse("ia:ver_resultado", args=[self.analysis.pk]))

        self.assertContains(response, "Experiencia registrada como Desarrolladora.")
        self.assertContains(response, "Habilidades detectadas: Python.")

    def test_resultado_conserva_resumen_anterior_si_el_nuevo_esta_vacio(self):
        self.analysis.perfil_snapshot = {**self.content, "summary": ""}
        self.analysis.save(update_fields=["perfil_snapshot"])

        response = self.client.get(reverse("ia:ver_resultado", args=[self.analysis.pk]))

        self.assertContains(response, "Perfil sintético.")

    def test_mi_perfil_reconstruye_resumen_si_el_guardado_esta_vacio(self):
        self.profile.contenido = {**self.content, "summary": None}
        self.profile.save(update_fields=["contenido"])

        response = self.client.get(reverse("mi_perfil"))

        self.assertContains(response, "Habilidades detectadas: Python.")
        self.assertContains(response, "Proyectos registrados: Sistema de turnos.")
