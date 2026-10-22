from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria, Habilidad
from cursos.models import Curso
from ia.models import EventoSalida
from ofertas.models import Oferta
from usuarios.models import Postulante, Usuario

from .models import ResultadoCompatibilidad


class CourseRecommendationViewTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(email='learning@example.invalid', password='synthetic-password')
        self.candidate = Postulante.objects.create(usuario=self.user)
        category = Categoria.objects.create(nombre='Administración sintética')
        self.offer = Oferta.objects.create(
            empresa=self.user, categoria=category, titulo='Ventas de prueba', nombre_puesto='Ventas',
            ubicacion='Resistencia', descripcion='Ventas con planillas.', habilidades_requeridas='Excel',
            nivel_educativo='secundario', estado='activa', fecha_cierre=timezone.now()+timedelta(days=7),
        )
        skill = Habilidad.objects.create(nombre='Excel', categoria=category, tipo_habilidad='D')
        self.specific = Curso.objects.create(
            nombre='Excel para el trabajo', descripcion='Planillas y fórmulas.', categoria=category,
            duracion='8 semanas', horario='A coordinar', tipo=Curso.VIRTUAL,
        )
        self.general = Curso.objects.create(
            nombre='Administración práctica', descripcion='Herramientas administrativas.', categoria=category,
            duracion='12 semanas', horario='A coordinar', tipo=Curso.VIRTUAL,
        )
        self.general.habilidades.add(skill)
        Curso.objects.create(nombre='Preparación para entrevistas', descripcion='Entrevistas.', categoria=category)
        self.match = ResultadoCompatibilidad.objects.create(
            postulante=self.candidate, oferta=self.offer, cache_key='c'*64,
            perfil_cv_version=1, perfil_oferta_version=1, perfil_cv_hash='a'*64, perfil_oferta_hash='b'*64,
            estado='completed', match_percentage=35, coverage_percentage=50,
            offer_snapshot={'requirements':[{'id':'req-excel', 'name':'Excel',
                'category':'technical_skills', 'mandatory':True}]},
            resultado={'summary':'Evaluación sintética.', 'mandatory_status':'not_met', 'breakdown':{},
                'assessments':[{'requirement_id':'req-excel', 'name':'Excel', 'category':'technical_skills',
                    'mandatory':True, 'status':'not_met', 'score':0,
                    'explanation':'No se alcanza el requisito de esta evaluación.'}]},
        )
        self.url = reverse('matching:detalle', args=[self.match.request_id])
        self.client.force_login(self.user)

    def test_specific_course_precedes_general_course_without_changing_match(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        recommendations = response.context['course_recommendations']['courses']
        self.assertEqual([row['course'].pk for row in recommendations], [self.specific.pk, self.general.pk])
        self.assertContains(response, 'id="course-recommendations"')
        self.assertContains(response, reverse('cursos:detalle', args=[self.specific.pk]))
        self.match.refresh_from_db()
        self.assertEqual(self.match.match_percentage, 35)
        self.assertEqual(self.match.resultado['assessments'][0]['status'], 'not_met')
        self.assertFalse(EventoSalida.objects.exists())

    def test_unknown_is_optional_and_met_does_not_generate_recommendations(self):
        for status in ['unknown', 'met']:
            with self.subTest(status=status):
                self.match.resultado['assessments'][0]['status'] = status
                self.match.save(update_fields=['resultado'])
                response = self.client.get(self.url)
                if status == 'unknown':
                    self.assertContains(response, 'Sin información suficiente en el CV')
                    self.assertTrue(response.context['course_recommendations']['gaps'][0]['optional'])
                else:
                    self.assertNotContains(response, 'id="course-recommendations"')

    def test_catalog_updates_without_recalculating_historical_result(self):
        self.specific.activo = False
        self.specific.save(update_fields=['activo'])
        self.offer.habilidades_requeridas = 'Otra habilidad'
        self.offer.save(update_fields=['habilidades_requeridas'])
        response = self.client.get(self.url)
        recommendations = response.context['course_recommendations']['courses']
        self.assertEqual([row['course'].pk for row in recommendations], [self.general.pk])
        self.assertEqual(response.context['course_recommendations']['gaps'][0]['name'], 'Excel')
        self.assertFalse(EventoSalida.objects.exists())

    def test_detail_and_recommendations_are_private(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        other = Usuario.objects.create_user(email='learning-other@example.invalid', password='synthetic-password')
        Postulante.objects.create(usuario=other)
        self.client.force_login(other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
