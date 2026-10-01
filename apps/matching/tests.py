from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from categorias.models import Categoria
from ia.models import EstadoPerfil, EventoSalida, PerfilCV, PerfilOferta
from ofertas.models import Oferta
from usuarios.models import Postulante, Usuario

from .models import ResultadoCompatibilidad
from .services import complete_match, get_or_create_match, match_request_payload


class MatchingServiceTests(TestCase):
    def setUp(self):
        candidate_user = Usuario.objects.create_user(email='candidate@example.com', password='test-password')
        self.postulante = Postulante.objects.create(usuario=candidate_user)
        company = Usuario.objects.create_user(email='company@example.com', password='test-password')
        category = Categoria.objects.create(nombre='Tecnología')
        self.oferta = Oferta.objects.create(
            empresa=company, categoria=category, titulo='Backend developer', nombre_puesto='Backend developer',
            ubicacion='Córdoba', modalidad='remoto', descripcion='Python role', habilidades_duras='Python',
            habilidades_requeridas='Python', nivel_educativo='universitario', fecha_cierre=timezone.now() + timedelta(days=7),
            estado='activa',
        )
        self.cv_profile = PerfilCV.objects.create(
            postulante=self.postulante, version=1, source_hash='a' * 64, estado=EstadoPerfil.LISTO,
            contenido={'schema_version': 'candidate-profile.v1', 'profile_id': str(self.postulante.pk), 'headline': 'Backend developer', 'summary': None, 'skills': [{'name': 'Python', 'level': 'advanced', 'evidence': []}], 'work_experience': [], 'education': [], 'languages': [], 'preferences': {'locations': [], 'work_modes': []}},
        )
        PerfilOferta.objects.create(
            oferta=self.oferta, version=1, source_hash='b' * 64, estado=EstadoPerfil.LISTO,
            contenido={'schema_version': 'job-offer.v1', 'offer_id': str(self.oferta.pk), 'title': 'Backend developer', 'summary': None, 'location': 'Córdoba', 'work_mode': 'remote', 'minimum_experience_months': None, 'education_levels': [], 'languages': [], 'requirements': [{'name': 'Python', 'minimum_level': 'intermediate', 'minimum_years': None, 'mandatory': True, 'exclusionary': False, 'evidence': []}]},
        )

    @patch('matching.services._read_cache', return_value=None)
    def test_same_versions_create_one_match_and_one_outbox_event(self, cache_read):
        first, created = get_or_create_match(self.postulante, self.oferta)
        second, created_again = get_or_create_match(self.postulante, self.oferta)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(EventoSalida.objects.filter(tipo=EventoSalida.Tipo.MATCH).count(), 1)

    @patch('matching.services._save_cache')
    @patch('matching.services._read_cache', return_value=None)
    @patch('matching.services._notify')
    def test_result_is_persisted_and_recoverable_from_db(self, notify, cache_read, cache_save):
        match, _ = get_or_create_match(self.postulante, self.oferta)
        payload = match_request_payload(match)
        result = {
            'schema_version': 'match-result.v1', 'request_id': payload['request_id'], 'status': 'completed',
            'match_percentage': 82, 'coverage_percentage': 100, 'confidence_percentage': 75,
            'assessments': [{'name': 'Python', 'score': 1, 'status': 'met', 'mandatory': True, 'explanation': 'Documented profile skill.'}],
            'summary': 'Strong skill alignment.',
        }
        completed = complete_match(str(match.request_id), result)
        completed.refresh_from_db()
        self.assertEqual(completed.estado, ResultadoCompatibilidad.Estado.COMPLETADO)
        self.assertEqual(float(completed.match_percentage), 82.0)
