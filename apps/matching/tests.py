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
from copy import deepcopy
from django.urls import reverse


class MatchingServiceTests(TestCase):
    def setUp(self):
        limiter = patch('matching.services._allow_new_request', return_value=True)
        limiter.start()
        self.addCleanup(limiter.stop)
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

    @patch('matching.services._read_cache', return_value=None)
    def test_same_content_from_different_candidate_is_not_shared(self, cache_read):
        first, _ = get_or_create_match(self.postulante, self.oferta)
        user = Usuario.objects.create_user(email='other@example.com', password='test-password')
        other = Postulante.objects.create(usuario=user)
        PerfilCV.objects.create(postulante=other, version=1, source_hash=self.cv_profile.source_hash,
                                estado=EstadoPerfil.LISTO, contenido=self.cv_profile.contenido)
        second, _ = get_or_create_match(other, self.oferta)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(second.postulante_id, other.pk)
        self.client.force_login(user)
        response = self.client.get(reverse('matching:estado', args=[first.request_id]))
        self.assertEqual(response.status_code, 404)

    @patch('matching.services._read_cache', return_value=None)
    def test_queued_match_keeps_original_profiles_after_edit(self, cache_read):
        match, _ = get_or_create_match(self.postulante, self.oferta)
        original = deepcopy(self.cv_profile.contenido)
        self.cv_profile.version = 2
        self.cv_profile.contenido['headline'] = 'Changed after queuing'
        self.cv_profile.save()
        match.refresh_from_db()
        payload = match_request_payload(match)
        self.assertEqual(payload['candidate_profile']['headline'], original['headline'])
        self.assertEqual(payload['metadata']['candidate_profile_version'], 1)

    def test_missing_profile_returns_conflict_instead_of_server_error(self):
        self.cv_profile.delete()
        self.client.force_login(self.postulante.usuario)
        response = self.client.post(reverse('matching:calcular', args=[self.oferta.pk]))
        self.assertEqual(response.status_code, 409)

    @patch('matching.services._read_cache', return_value=None)
    def test_updated_profile_hides_previous_result(self, cache_read):
        match, _ = get_or_create_match(self.postulante, self.oferta)
        match.estado = 'completed'
        match.match_percentage = 82
        match.save()
        self.cv_profile.version = 2
        self.cv_profile.save()
        self.client.force_login(self.postulante.usuario)
        from ofertas.views import detalle_oferta_postulante
        from django.test import RequestFactory
        request = RequestFactory().get('/')
        request.user = self.postulante.usuario
        with patch('ofertas.views.render') as render:
            detalle_oferta_postulante(request, self.oferta.pk)
        self.assertIsNone(render.call_args.args[2]['match'])

    @patch('matching.services._read_cache', return_value=None)
    def test_failed_match_can_be_retried_as_new_execution(self, cache_read):
        first, _ = get_or_create_match(self.postulante, self.oferta)
        old_id = first.request_id
        first.estado = 'error'
        first.save()
        retried, created = get_or_create_match(self.postulante, self.oferta)
        self.assertTrue(created)
        self.assertNotEqual(retried.request_id, old_id)
        self.assertEqual(retried.estado, 'pending')

    @patch('matching.services._read_cache', return_value=None)
    def test_offer_page_displays_zero_percentage_and_keeps_recovery_id(self, cache_read):
        match, _ = get_or_create_match(self.postulante, self.oferta)
        match.estado = 'completed'
        match.match_percentage = 0
        match.save()
        from django.test import RequestFactory
        from ofertas.views import detalle_oferta_postulante
        request = RequestFactory().get('/')
        request.user = self.postulante.usuario
        response = detalle_oferta_postulante(request, self.oferta.pk)
        self.assertContains(response, '>0%</span>')
        self.assertContains(response, f'data-request-id="{match.request_id}"')
        self.assertContains(response, 'Requisitos con información')
