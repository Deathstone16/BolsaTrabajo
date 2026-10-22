"""Deterministic recommendations from synthetic historical gaps and live catalog."""

from copy import deepcopy
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from categorias.models import Categoria, Habilidad
from cursos.models import Curso
from ofertas.models import Oferta
from usuarios.models import Postulante, Usuario

from .course_recommendations import recommend_courses_for_match
from .models import ResultadoCompatibilidad


class CourseRecommendationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Categoria.objects.create(nombre='Administración')
        cls.tech = Categoria.objects.create(nombre='Tecnología')
        company = Usuario.objects.create_user(email='courses-company@example.invalid')
        applicant = Usuario.objects.create_user(email='courses-candidate@example.invalid')
        cls.candidate = Postulante.objects.create(usuario=applicant)
        cls.offer = Oferta.objects.create(
            empresa=company, categoria=cls.admin, titulo='Puesto sintético',
            nombre_puesto='Puesto sintético', ubicacion='Ciudad sintética',
            descripcion='Oferta sintética.', habilidades_requeridas='Excel',
            nivel_educativo='secundario', fecha_cierre=timezone.now(), estado='activa',
        )

    def course(self, name, *, description='', category=None, active=True, skills=()):
        course = Curso.objects.create(
            nombre=name, descripcion=description, categoria=category or self.admin,
            imagen='synthetic-course.png', duracion='20 horas', horario='A coordinar', activo=active,
        )
        for skill in skills:
            if isinstance(skill, str):
                skill, _ = Habilidad.objects.get_or_create(nombre=skill, categoria=course.categoria)
            course.habilidades.add(skill)
        return course

    def match(self, names=('Excel',), *, statuses=None, categories=None, mandatory=None,
              requirements=None, state='completed'):
        statuses = statuses or ['not_met'] * len(names)
        categories = categories or ['technical_skills'] * len(names)
        mandatory = mandatory or [True] * len(names)
        if requirements is None:
            requirements = [
                {'id': f'req-{index}', 'name': name, 'category': category, 'mandatory': required}
                for index, (name, category, required) in enumerate(zip(names, categories, mandatory))
            ]
        assessments = [
            {'requirement_id': f'req-{index}', 'name': name, 'category': category,
             'mandatory': required, 'status': status}
            for index, (name, category, required, status) in enumerate(zip(names, categories, mandatory, statuses))
        ]
        match = ResultadoCompatibilidad.objects.create(
            postulante=self.candidate, oferta=self.offer, cache_key=uuid4().hex,
            estado=state, perfil_cv_version=1, perfil_oferta_version=1,
            perfil_cv_hash='a' * 64, perfil_oferta_hash='b' * 64,
            offer_snapshot={'schema_version': 'job-offer.v2', 'requirements': requirements},
            resultado={'assessments': assessments, 'match_percentage': 42},
        )
        return ResultadoCompatibilidad.objects.select_related('oferta__categoria').get(pk=match.pk)

    def test_title_precedes_curated_skill_then_description_and_excludes_general_and_inactive(self):
        direct = self.course('Curso de Excel')
        curated = self.course('Administración profesional', skills=['Excel'])
        described = self.course('Herramientas de oficina', description='Práctica de Excel para tareas habituales.')
        general = self.course('Administración general')
        inactive = self.course('Excel intensivo', active=False)
        result = recommend_courses_for_match(self.match())
        self.assertEqual([card['course'].pk for card in result['courses']], [direct.pk, curated.pk, described.pk])
        self.assertEqual([card['match_type'] for card in result['courses']], ['title', 'skill', 'description'])
        self.assertIn('Excel', result['courses'][1]['reason'])
        self.assertNotIn(general.pk, [card['course'].pk for card in result['courses']])
        self.assertNotIn(inactive.pk, [card['course'].pk for card in result['courses']])

    def test_polluted_skill_categories_do_not_imply_course_coverage(self):
        for category in (self.admin, self.tech, Categoria.objects.create(nombre='Marketing')):
            Habilidad.objects.create(nombre='Excel', categoria=category)
        self.course('Seguridad en el trabajo', category=self.admin)
        self.course('Marketing digital', category=self.tech)
        result = recommend_courses_for_match(self.match())
        self.assertTrue(result['has_gaps'])
        self.assertFalse(result['no_catalog'])
        self.assertEqual(result['courses'], [])

    def test_curated_skill_works_across_offer_and_taxonomy_categories(self):
        excel_other_area = Habilidad.objects.create(nombre='Excel', categoria=self.tech)
        course = self.course('Administración de organizaciones', category=self.admin, skills=[excel_other_area])
        self.offer.categoria = self.tech
        self.offer.save(update_fields=['categoria'])
        result = recommend_courses_for_match(self.match())
        self.assertEqual(result['courses'][0]['course'].pk, course.pk)
        self.assertEqual(result['courses'][0]['match_type'], 'skill')
        self.assertIn('Excel', result['courses'][0]['reason'])

    def test_general_related_only_without_specific_coverage_and_exact_current_offer_area(self):
        general = self.course('Introducción a la Administración general')
        other_area = self.course('Tecnología general', category=self.tech)
        self.course('Contabilidad específica', category=self.admin)
        match = self.match()
        first = recommend_courses_for_match(match)
        self.assertEqual([card['course'].pk for card in first['courses']], [general.pk])
        self.assertEqual(first['courses'][0]['match_type'], 'related')
        self.assertIn('revisá si su temario cubre Excel', first['courses'][0]['reason'])
        # Only catalog navigation follows the current area; the frozen gap stays Excel.
        self.offer.categoria = self.tech
        self.offer.save(update_fields=['categoria'])
        match = ResultadoCompatibilidad.objects.select_related('oferta__categoria').get(pk=match.pk)
        second = recommend_courses_for_match(match)
        self.assertEqual([card['course'].pk for card in second['courses']], [other_area.pk])
        self.assertEqual(second['gaps'][0]['name'], 'Excel')
        self.assertEqual(second['gaps'][0]['category'], 'technical_skills')

    def test_even_description_specificity_suppresses_general_related(self):
        general = self.course('Administración general')
        described = self.course('Herramientas para oficina', description='Incluye práctica de Excel.')
        result = recommend_courses_for_match(self.match())
        self.assertEqual([card['course'].pk for card in result['courses']], [described.pk])
        self.assertNotEqual(result['courses'][0]['course'].pk, general.pk)

    def test_unknown_is_optional_and_never_confirms_a_missing_skill(self):
        self.course('Excel')
        result = recommend_courses_for_match(self.match(statuses=['unknown']))
        gap = result['gaps'][0]
        self.assertEqual(gap['status_label'], 'Sin información')
        self.assertTrue(gap['optional'])
        self.assertTrue(result['courses'][0]['optional'])
        self.assertIn('Sugerencia opcional', gap['courses'][0]['reason'])
        self.assertIn('no hay información suficiente', gap['courses'][0]['reason'])
        self.assertNotIn('te falta', gap['courses'][0]['reason'].lower())

    def test_years_logistics_degrees_and_licenses_are_not_course_gaps(self):
        names = ['Excel', 'Presencial', 'Título universitario', 'Licencia de conducir B',
                 '3 años de Excel', 'Excel', 'Tres años de experiencia en soldadura']
        categories = ['experience', 'logistics', 'education', 'desirables',
                      'technical_skills', 'technical_skills', 'desirables']
        requirements = [{'id': f'req-{i}', 'name': name, 'category': category, 'mandatory': True}
                        for i, (name, category) in enumerate(zip(names, categories))]
        requirements[5]['minimum_years'] = 3
        self.course('Excel')
        result = recommend_courses_for_match(self.match(names, categories=categories, requirements=requirements))
        self.assertFalse(result['has_gaps'])
        self.assertFalse(result['no_catalog'])
        self.assertEqual(result['courses'], [])

    def test_word_boundaries_separate_java_javascript_r_react_and_c_variants(self):
        java = self.course('Programación Java', category=self.tech)
        r_course = self.course('Análisis de datos con R', category=self.tech)
        cpp = self.course('Introducción a C++', category=self.tech)
        wrong = [self.course('JavaScript'), self.course('React'), self.course('C#')]
        result = recommend_courses_for_match(self.match(['Java', 'R', 'C++']))
        self.assertEqual({card['course'].pk for card in result['courses']}, {java.pk, r_course.pk, cpp.pk})
        self.assertFalse({course.pk for course in wrong} & {card['course'].pk for card in result['courses']})

    def test_accents_stop_words_and_common_vendor_alias_are_normalized(self):
        communication = self.course('Comunicación al cliente')
        excel = self.course('Excel inicial')
        result = recommend_courses_for_match(self.match(['Manejo avanzado de comunicación al cliente', 'Microsoft Excel']))
        self.assertEqual({card['course'].pk for card in result['courses']}, {communication.pk, excel.pk})

    def test_negative_mentions_do_not_claim_description_coverage(self):
        self.course('Gestión de oficina', description='No incluye Excel.')
        self.course('Administración sin Excel')
        result = recommend_courses_for_match(self.match())
        self.assertEqual(result['courses'], [])

    def test_prerequisites_are_not_course_coverage(self):
        self.course('Análisis con otras herramientas', description='Requisitos: SQL.')
        self.course('Reportes de datos', description='Requiere conocimientos previos de SQL.')
        positive = self.course('Bases de datos iniciales', description='El programa enseña SQL desde cero.')
        result = recommend_courses_for_match(self.match(['SQL']))
        self.assertEqual([card['course'].pk for card in result['courses']], [positive.pk])

    def test_no_catalog_distinguishes_empty_from_irrelevant_active_catalog(self):
        match = self.match()
        self.assertTrue(recommend_courses_for_match(match)['no_catalog'])
        self.course('Arte con materiales reciclados')
        result = recommend_courses_for_match(match)
        self.assertFalse(result['no_catalog'])
        self.assertEqual(result['courses'], [])

    def test_sectors_support_independent_curated_skills(self):
        health = self.course('Cuidados iniciales', skills=['Primeros auxilios'])
        welding = self.course('Prácticas de taller', skills=['Soldadura'])
        soft = self.course('Atención de consultas', skills=['Comunicación'])
        result = recommend_courses_for_match(self.match(
            ['Primeros auxilios', 'Soldadura', 'Comunicación'],
            categories=['technical_skills', 'technical_skills', 'soft_skills'],
        ))
        self.assertEqual({card['course'].pk for card in result['courses']}, {health.pk, welding.pk, soft.pk})

    def test_one_course_for_multiple_gaps_has_one_global_card_and_all_explanations(self):
        course = self.course('Herramientas de oficina', skills=['Excel', 'Word'])
        result = recommend_courses_for_match(self.match(['Excel', 'Word'], statuses=['partial', 'unknown']))
        self.assertEqual(len(result['courses']), 1)
        card = result['courses'][0]
        self.assertEqual(card['course'].pk, course.pk)
        self.assertEqual([gap['name'] for gap in card['gaps']], ['Excel', 'Word'])
        self.assertIn('Excel', card['reason'])
        self.assertIn('Word', card['reason'])
        self.assertFalse(card['optional'])
        self.assertTrue(all(gap['courses'][0]['course'].pk == course.pk for gap in result['gaps']))

    def test_priority_and_per_gap_global_limits(self):
        names = ['Opcional', 'Parcial', 'Deseable', 'Obligatoria']
        for name in names:
            for index in range(4):
                self.course(f'Curso {name} {index}')
        result = recommend_courses_for_match(self.match(
            names, statuses=['unknown', 'partial', 'not_met', 'not_met'], mandatory=[True, True, False, True],
        ))
        self.assertEqual([gap['name'] for gap in result['gaps']], ['Obligatoria', 'Deseable', 'Parcial', 'Opcional'])
        self.assertEqual(len(result['courses']), 6)
        self.assertEqual(len({card['course'].pk for card in result['courses']}), 6)
        self.assertTrue(all(len(gap['courses']) <= 3 for gap in result['gaps']))
        self.assertEqual([len(gap['courses']) for gap in result['gaps']], [3, 3, 0, 0])

    def test_catalog_changes_are_live_and_completed_match_is_unchanged(self):
        old = self.course('Excel')
        match = self.match()
        before = deepcopy((match.offer_snapshot, match.resultado, match.match_percentage, match.estado))
        self.assertEqual(recommend_courses_for_match(match)['courses'][0]['course'].pk, old.pk)
        old.activo = False
        old.save(update_fields=['activo'])
        new = self.course('Administración práctica')
        self.assertEqual(recommend_courses_for_match(match)['courses'], [])
        skill = Habilidad.objects.create(nombre='Excel', categoria=self.tech)
        new.habilidades.add(skill)
        self.assertEqual(recommend_courses_for_match(match)['courses'][0]['course'].pk, new.pk)
        match.refresh_from_db()
        self.assertEqual((match.offer_snapshot, match.resultado, match.match_percentage, match.estado), before)

    def test_frozen_requirement_name_category_and_mandatory_are_authoritative(self):
        excel = self.course('Excel')
        self.course('Word')
        match = self.match(mandatory=[False])
        match.resultado['assessments'][0].update(name='Word', category='logistics', mandatory=True)
        self.offer.requisitos_estructurados = [{'id': 'req-0', 'name': 'Word', 'category': 'education'}]
        self.offer.save(update_fields=['requisitos_estructurados'])
        result = recommend_courses_for_match(match)
        self.assertEqual(result['gaps'][0]['name'], 'Excel')
        self.assertEqual(result['gaps'][0]['category'], 'technical_skills')
        self.assertFalse(result['gaps'][0]['mandatory'])
        self.assertEqual(result['courses'][0]['course'].pk, excel.pk)

    def test_missing_and_repeated_requirement_ids_do_not_add_unfrozen_gaps(self):
        self.course('Excel')
        match = self.match()
        match.resultado['assessments'] += [
            deepcopy(match.resultado['assessments'][0]),
            {'requirement_id': 'unknown', 'name': 'Word', 'category': 'technical_skills', 'status': 'not_met'},
        ]
        self.assertEqual(len(recommend_courses_for_match(match)['gaps']), 1)

    def test_legacy_without_requirements_uses_assessment_category(self):
        course = self.course('Excel')
        match = self.match(requirements=[])
        match.resultado['assessments'][0].pop('requirement_id')
        result = recommend_courses_for_match(match)
        self.assertEqual(result['courses'][0]['course'].pk, course.pk)
        self.assertIsNone(result['gaps'][0]['requirement_id'])

    def test_null_requirement_id_resolves_only_a_unique_frozen_name_and_category(self):
        course = self.course('Excel')
        requirement = {'id': None, 'name': 'Excel', 'category': 'technical_skills', 'mandatory': False}
        match = self.match(requirements=[requirement])
        match.resultado['assessments'][0].update(requirement_id=None, name=' EXCEL ', mandatory=True)
        result = recommend_courses_for_match(match)
        self.assertEqual(result['courses'][0]['course'].pk, course.pk)
        self.assertEqual(result['gaps'][0]['name'], 'Excel')
        self.assertFalse(result['gaps'][0]['mandatory'])
        # Ambiguous frozen names never fall back to the current offer or guessed identity.
        match.offer_snapshot['requirements'].append({**requirement, 'mandatory': True})
        self.assertEqual(recommend_courses_for_match(match)['gaps'], [])

    def test_met_and_nonterminal_results_do_not_query_the_catalog(self):
        for state, status in [('pending', 'not_met'), ('error', 'not_met'), ('completed', 'met')]:
            match = self.match(state=state, statuses=[status])
            with self.assertNumQueries(0):
                self.assertEqual(recommend_courses_for_match(match),
                                 {'gaps': [], 'courses': [], 'has_gaps': False, 'no_catalog': False})

    def test_catalog_prefetch_keeps_queries_constant_across_gaps(self):
        for index in range(5):
            self.course(f'Curso sintético {index}', skills=['Excel', 'Word', 'Comunicación'])
        match = self.match(['Excel', 'Word', 'Comunicación'])
        with self.assertNumQueries(2):
            result = recommend_courses_for_match(match)
        self.assertTrue(result['courses'])
