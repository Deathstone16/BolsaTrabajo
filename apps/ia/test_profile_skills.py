"""Pruebas semánticas para la presentación de habilidades del perfil."""

from copy import deepcopy
from enum import Enum

from django.test import SimpleTestCase

from .profile_skills import split_profile_skills


class SkillKind(str, Enum):
    SOFT = 'soft'
    TECHNICAL = 'technical'


class SplitProfileSkillsTests(SimpleTestCase):
    def test_tipo_explicito_prevalece_sobre_el_nombre(self):
        content = {
            'skills': [
                {'name': 'Orientación al cliente', 'kind': SkillKind.SOFT},
                {'name': 'Comunicación efectiva', 'kind': 'soft'},
                {'name': 'Comunicación', 'kind': SkillKind.TECHNICAL},
                {'name': 'Liderazgo', 'kind': 'technical'},
            ],
        }

        hard, soft = split_profile_skills(content)

        self.assertEqual([skill['name'] for skill in soft], [
            'Orientación al cliente', 'Comunicación efectiva',
        ])
        self.assertEqual([skill['name'] for skill in hard], ['Comunicación', 'Liderazgo'])

    def test_whitelist_se_usa_para_tipo_unknown_o_ausente(self):
        content = {
            'skills': [
                {'name': 'Teamwork', 'kind': 'unknown'},
                {'name': 'Python', 'kind': 'unknown'},
                {'name': 'Comunicación', 'level': 'intermediate'},
                {'name': 'SQL', 'level': 'advanced'},
            ],
        }

        hard, soft = split_profile_skills(content)

        self.assertEqual([skill['name'] for skill in soft], ['Teamwork', 'Comunicación'])
        self.assertEqual([skill['name'] for skill in hard], ['Python', 'SQL'])

    def test_clasificacion_conserva_orden_datos_y_no_muta_el_contenido(self):
        content = {
            'skills': [
                {'name': 'Liderazgo', 'kind': 'technical', 'evidence': ['A']},
                {'name': 'Colaboración', 'kind': 'soft', 'origin': 'declared'},
                {'name': 'Trabajo en equipo'},
                {'name': 'Django', 'kind': 'technical'},
                {'name': 'Empathy', 'kind': 'soft'},
            ],
            'summary': 'Perfil de prueba',
        }
        original = deepcopy(content)

        hard, soft = split_profile_skills(content)

        self.assertEqual([skill['name'] for skill in hard], ['Liderazgo', 'Django'])
        self.assertEqual([skill['name'] for skill in soft], [
            'Colaboración', 'Trabajo en equipo', 'Empathy',
        ])
        self.assertEqual(content, original)
        self.assertIs(hard[0], content['skills'][0])
        self.assertIs(soft[0], content['skills'][1])

    def test_taxonomia_explicita_desconocida_no_activa_la_whitelist(self):
        content = {'skills': [{'name': 'Comunicación', 'kind': 'domain_specific'}]}

        hard, soft = split_profile_skills(content)

        self.assertEqual([skill['name'] for skill in hard], ['Comunicación'])
        self.assertEqual(soft, [])
