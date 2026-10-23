import json
from datetime import timedelta
from decimal import Decimal
from html.parser import HTMLParser
from unittest.mock import patch

from django.core.exceptions import ValidationError
from asgiref.sync import async_to_sync
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from ia.models import CVVersion, EstadoPerfil, EventoSalida, PerfilCV, PerfilOferta, TrabajoExtraccion
from ia.workflow import offer_snapshot, request_offer_extraction
from ofertas.models import Oferta
from usuarios.models import Postulante, Usuario

from .configuration import publish_configuration, scoring_hash
from .models import ConfiguracionActiva, ConfiguracionCompatibilidad, ResultadoCompatibilidad
from .services import complete_match, get_or_create_match, match_request_payload
from .services import status_payload


def html_attributes_by_id(response):
    class Elements(HTMLParser):
        def __init__(self):
            super().__init__()
            self.elements = {}

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if values.get('id'):
                self.elements[values['id']] = values

    parser = Elements()
    parser.feed(response.content.decode())
    return parser.elements


class MatchingServiceTests(TestCase):
    def setUp(self):
        limiter = patch('matching.services._allow_new_request', return_value=True)
        limiter.start()
        self.addCleanup(limiter.stop)
        cache = patch('matching.services._read_cache', return_value=None)
        cache.start()
        self.addCleanup(cache.stop)
        self.candidate_user = Usuario.objects.create_user(email='candidate@example.com', password='test-password')
        self.postulante = Postulante.objects.create(usuario=self.candidate_user)
        self.cv_version = CVVersion.objects.create(
            postulante=self.postulante, numero=1,
            archivo=SimpleUploadedFile('cv.txt', b'Python developer'),
            nombre_original='cv.txt', sha256='a' * 64, formato='txt', tamano=15,
        )
        self.postulante.cv_version_actual = self.cv_version
        self.postulante.save(update_fields=['cv_version_actual'])
        self.cv_profile = PerfilCV.objects.create(
            postulante=self.postulante, cv_version=self.cv_version, version=1,
            source_hash='b' * 64, schema_version='candidate-profile.v2', estado=EstadoPerfil.LISTO,
            contenido={
                'schema_version': 'candidate-profile.v2', 'profile_id': str(self.postulante.pk),
                'headline': 'Backend developer', 'summary': None,
                'skills': [{'name': 'Python', 'level': 'advanced', 'evidence': ['Listed as a skill'],
                            'source_quotes': ['Python'], 'kind': 'technical', 'origin': 'declared'}],
                'work_experience': [], 'education': [], 'languages': [], 'credentials': [],
                'preferences': {'locations': [], 'work_modes': []}, 'rejected_skills': [],
            },
        )
        company = Usuario.objects.create_user(email='company@example.com', password='test-password')
        category = Categoria.objects.create(nombre='Tecnología')
        self.oferta = Oferta.objects.create(
            empresa=company, categoria=category, titulo='Backend developer', nombre_puesto='Backend developer',
            ubicacion='Córdoba', modalidad='remoto', descripcion='Python role', habilidades_duras='Python',
            habilidades_requeridas='Python', requisitos_obligatorios='Python',
            requisitos_estructurados=[{'id': 'req-python', 'category': 'technical_skills',
                'source': 'requisitos_obligatorios', 'name': 'Python', 'mandatory': True, 'exclusionary': False}],
            requiere_revision_requisitos=False, nivel_educativo='universitario',
            fecha_cierre=timezone.now() + timedelta(days=7), estado='activa',
        )
        self.offer_profile = PerfilOferta.objects.create(
            oferta=self.oferta, version=1, source_hash='c' * 64, schema_version='job-offer.v2',
            estado=EstadoPerfil.LISTO,
            contenido={
                **offer_snapshot(self.oferta), 'requirements': self.oferta.requisitos_estructurados,
            },
        )
        job, _ = request_offer_extraction(self.oferta)
        job.estado = TrabajoExtraccion.Estado.COMPLETADO
        job.save(update_fields=['estado', 'actualizado_en'])
        self.offer_profile.estado = EstadoPerfil.LISTO
        self.offer_profile.save(update_fields=['estado', 'actualizado_en'])
        self.config = ConfiguracionActiva.objects.get(singleton='actual').configuracion

    def tearDown(self):
        for version in self.postulante.versiones_cv.all():
            version.archivo.delete(save=False)
        super().tearDown()

    def test_detalle_organiza_resultado_y_escapa_explicaciones(self):
        match, _ = get_or_create_match(self.postulante, self.oferta)
        match.estado = 'completed'
        match.match_percentage = 82
        match.coverage_percentage = 100
        match.resultado = {
            'mandatory_status': 'all_met', 'summary': 'Resumen de compatibilidad.',
            'assessments': [{'name': 'Python', 'status': 'met', 'mandatory': True,
                             'explanation': '<script>alert(1)</script>',
                             'points_awarded': 82, 'points_possible': 100}],
            'breakdown': {'technical_skills': {'score': 1, 'applicable': True, 'configured_weight_bp': 3500}},
        }
        match.save()
        self.client.force_login(self.candidate_user)
        response = self.client.get(reverse('matching:detalle', args=[match.request_id]))
        self.assertContains(response, '82%')
        self.assertContains(response, '82,00 de 100 puntos obtenidos')
        self.assertContains(response, '82,00 / 100,00 puntos')
        self.assertContains(response, 'Compatibilidad por área')
        self.assertContains(response, 'Requisitos obligatorios')
        self.assertContains(response, 'Coincide')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_detalle_es_privado_y_no_inicia_otra_solicitud(self):
        match, _ = get_or_create_match(self.postulante, self.oferta)
        url = reverse('matching:detalle', args=[match.request_id])
        self.assertEqual(self.client.get(url).status_code, 302)
        other = Usuario.objects.create_user(email='other-match@example.com', password='test-password')
        Postulante.objects.create(usuario=other)
        self.client.force_login(other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.candidate_user)
        count = EventoSalida.objects.count()
        self.assertContains(self.client.get(url), 'El resultado todavía no está listo')
        self.assertEqual(EventoSalida.objects.count(), count)

    @patch('matching.services._save_cache')
    def test_oferta_recupera_match_completado_y_link_sin_otro_calculo(self, _cache):
        match, _ = get_or_create_match(self.postulante, self.oferta)
        match.estado = 'completed'
        match.match_percentage = 82
        match.resultado = {'mandatory_status': 'all_met', 'assessments': [], 'breakdown': {}}
        match.save()
        self.client.force_login(self.candidate_user)
        count = EventoSalida.objects.count()
        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))
        elements = html_attributes_by_id(response)
        self.assertEqual(elements['match-card']['data-request-id'], str(match.request_id))
        self.assertEqual(elements['match-card']['data-status'], 'completed')
        self.assertNotIn('is-calculating', elements['match-card']['class'])
        self.assertEqual(float(elements['match-progress']['data-value']), 82)
        self.assertContains(response, '>82%</span>')
        self.assertNotIn('hidden', elements['match-details-action'])
        self.assertEqual(elements['match-details-link']['href'], reverse('matching:detalle', args=[match.request_id]))
        self.assertIn('hidden', elements['match-form'])
        self.assertEqual(EventoSalida.objects.count(), count)

    @patch('matching.services._save_cache')
    def test_cero_es_un_resultado_valido_y_no_un_estado_de_carga(self, _cache):
        match, _ = get_or_create_match(self.postulante, self.oferta)
        match.estado = 'completed'
        match.match_percentage = 0
        match.save()
        self.client.force_login(self.candidate_user)
        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))
        elements = html_attributes_by_id(response)
        self.assertEqual(float(elements['match-progress']['data-value']), 0)
        self.assertNotIn('is-calculating', elements['match-card']['class'])
        self.assertContains(response, '>0%</span>')
        self.assertNotIn('hidden', elements['match-details-action'])

    @patch('matching.services._save_cache')
    def test_match_pendiente_se_recupera_con_espera_sin_porcentaje_ficticio(self, _cache):
        match, _ = get_or_create_match(self.postulante, self.oferta)
        self.client.force_login(self.candidate_user)
        count = EventoSalida.objects.count()
        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))
        elements = html_attributes_by_id(response)
        self.assertEqual(elements['match-card']['data-request-id'], str(match.request_id))
        self.assertEqual(elements['match-card']['data-status'], match.estado)
        self.assertIn('is-calculating', elements['match-card']['class'])
        self.assertEqual(elements['match-progress']['data-value'], '')
        self.assertContains(response, '>Calculando</span>')
        self.assertNotContains(response, '>0%</span>')
        self.assertIn('disabled', elements['match-button'])
        self.assertEqual(EventoSalida.objects.count(), count)

    def test_sin_match_se_muestra_sin_calcular_y_no_un_cero(self):
        self.client.force_login(self.candidate_user)
        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))
        self.assertContains(response, '>Sin calcular</span>')
        self.assertNotContains(response, '>0%</span>')
        self.assertFalse(ResultadoCompatibilidad.objects.exists())

    def test_oferta_legacy_explica_revision_y_no_ofrece_un_calculo_bloqueado(self):
        self.oferta.requiere_revision_requisitos = True
        self.oferta.save(update_fields=['requiere_revision_requisitos'])
        self.offer_profile.schema_version = 'job-offer.v1'
        self.offer_profile.save(update_fields=['schema_version'])
        self.client.force_login(self.candidate_user)
        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))
        self.assertContains(response, 'id="match-requisitos-pendientes"')
        self.assertContains(response, 'La empresa debe actualizar los requisitos')
        self.assertNotContains(response, 'id="match-form"')
        with self.assertRaisesMessage(ValueError, 'revisar sus requisitos'):
            get_or_create_match(self.postulante, self.oferta)
        self.assertFalse(ResultadoCompatibilidad.objects.exists())

    def test_revision_pendiente_bloquea_incluso_un_perfil_v2_antiguo(self):
        self.oferta.requiere_revision_requisitos = True
        self.oferta.save(update_fields=['requiere_revision_requisitos'])
        with self.assertRaisesMessage(ValueError, 'revisar sus requisitos'):
            get_or_create_match(self.postulante, self.oferta)
        self.assertFalse(ResultadoCompatibilidad.objects.exists())

    def test_perfil_v1_revisado_no_muestra_el_boton_hasta_actualizar_el_analisis(self):
        self.offer_profile.schema_version = 'job-offer.v1'
        self.offer_profile.save(update_fields=['schema_version'])
        self.client.force_login(self.candidate_user)
        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))
        self.assertContains(response, 'Esta oferta está siendo analizada.')
        self.assertNotContains(response, 'id="match-form"')

    @patch('matching.services._save_cache')
    def test_match_usa_v2_y_congela_perfiles_y_configuracion(self, save_cache):
        match, created = get_or_create_match(self.postulante, self.oferta)
        self.assertTrue(created)
        self.assertEqual(EventoSalida.objects.filter(tipo=EventoSalida.Tipo.MATCH).count(), 1)
        payload = match_request_payload(match)
        self.assertEqual(payload['protocol_version'], 'match.v2')
        self.assertEqual(payload['scoring_config']['weights'], self.config.pesos_basis_points())
        self.assertEqual(payload['metadata']['evaluation_date'], timezone.localdate().isoformat())
        self.cv_profile.contenido['headline'] = 'Changed after queue'
        self.cv_profile.save()
        payload = match_request_payload(match)
        self.assertEqual(payload['candidate_profile']['headline'], 'Backend developer')

    def test_dispatch_match_recupera_un_lease_vencido(self):
        from datetime import timedelta
        from django.utils import timezone
        from matching.management.commands.dispatch_match_jobs import Command
        get_or_create_match(self.postulante, self.oferta)
        event = EventoSalida.objects.get(tipo=EventoSalida.Tipo.MATCH)
        command = Command()
        self.assertEqual(command._claim().pk, event.pk)
        EventoSalida.objects.filter(pk=event.pk).update(actualizado_en=timezone.now() - timedelta(minutes=10))
        self.assertEqual(command._claim().pk, event.pk)

    @patch('matching.management.commands.dispatch_match_jobs.complete_match')
    @patch('matching.management.commands.dispatch_match_jobs.connect')
    def test_dispatch_match_espera_resultado_tras_aceptar_job_ya_completado(self, connect, complete):
        from matching.management.commands.dispatch_match_jobs import Command
        match, _ = get_or_create_match(self.postulante, self.oferta)
        event = EventoSalida.objects.get(tipo=EventoSalida.Tipo.MATCH)
        socket = connect.return_value.__enter__.return_value
        socket.recv.side_effect = [
            json.dumps({'type': 'match.accepted', 'status': 'completed', 'request_id': str(match.request_id)}),
            json.dumps({'type': 'match.completed', 'status': 'completed', 'result': {'request_id': str(match.request_id)}}),
        ]

        Command()._send(event)

        event.refresh_from_db()
        self.assertEqual(event.estado, EventoSalida.Estado.ENVIADO)
        complete.assert_called_once_with(str(match.request_id), {'request_id': str(match.request_id)})

    @patch('matching.services._save_cache')
    def test_callback_v2_rechaza_clasificacion_distinta_y_preserva_config_capturada(self, save_cache):
        match, _ = get_or_create_match(self.postulante, self.oferta)
        payload = match_request_payload(match)
        result = {
            'schema_version': 'match-result.v2', 'request_id': payload['request_id'], 'status': 'completed',
            'match_percentage': 100, 'coverage_percentage': 100, 'confidence_percentage': None,
            'confidence_available': False,
            'assessments': [{'requirement_id': 'req-python', 'category': 'soft_skills',
                'source': 'requisitos_obligatorios', 'name': 'Python', 'score': 1,
                'status': 'met', 'mandatory': True, 'explanation': 'Evidence found.',
                'evidence_refs': ['/skills/0/source_quotes/0'],
                'points_awarded': 100, 'points_possible': 100}],
            'summary': 'Match.', 'breakdown': {
                key: {'score': 1, 'configured_weight_bp': weight, 'effective_weight_bp': weight, 'applicable': True}
                for key, weight in payload['scoring_config']['weights'].items()
            },
            'scoring_config': payload['scoring_config'], 'mandatory_status': 'all_met',
            'provider_model': 'groq:test-model',
        }
        with self.assertRaises(ValueError):
            complete_match(str(match.request_id), result)
        result['assessments'][0]['category'] = 'technical_skills'
        result['match_percentage'] = 82
        with self.assertRaisesMessage(ValueError, 'suma de puntos'):
            complete_match(str(match.request_id), result)
        result['match_percentage'] = 100
        completed = complete_match(str(match.request_id), result)
        self.assertEqual(completed.estado, ResultadoCompatibilidad.Estado.COMPLETADO)
        self.assertIsNone(completed.confidence_percentage)
        self.assertEqual(completed.model_version, 'groq:test-model')
        self.assertEqual(completed.scoring_config_hash, scoring_hash(self.config))

    def test_no_calcula_con_perfil_de_un_cv_anterior(self):
        other = CVVersion.objects.create(
            postulante=self.postulante, numero=2,
            archivo=SimpleUploadedFile('new.txt', b'new'), nombre_original='new.txt',
            sha256='d' * 64, formato='txt', tamano=3,
        )
        self.postulante.cv_version_actual = other
        self.postulante.save(update_fields=['cv_version_actual'])
        with self.assertRaisesMessage(ValueError, 'versión actual'):
            get_or_create_match(self.postulante, self.oferta)

    def test_no_calcula_con_el_cv_cacheado_antes_de_una_carga_nueva(self):
        newer = CVVersion.objects.create(
            postulante=self.postulante, numero=2, archivo='synthetic-stale.txt',
            nombre_original='synthetic.txt', sha256='d' * 64, formato='txt', tamano=10,
        )
        Postulante.objects.filter(pk=self.postulante.pk).update(cv_version_actual=newer)
        with self.assertRaisesMessage(ValueError, 'versión actual'):
            get_or_create_match(self.postulante, self.oferta)
        self.assertFalse(ResultadoCompatibilidad.objects.exists())

    def test_no_calcula_con_la_oferta_cacheada_antes_de_una_edicion(self):
        Oferta.objects.filter(pk=self.oferta.pk).update(titulo='New title committed elsewhere')
        with self.assertRaisesMessage(ValueError, 'La oferta cambió'):
            get_or_create_match(self.postulante, self.oferta)
        self.assertFalse(ResultadoCompatibilidad.objects.exists())

    def test_offer_callback_a_after_b_is_stale(self):
        from ia.workflow import receive_extraction_event
        job_a = TrabajoExtraccion.objects.filter(oferta=self.oferta, tipo=TrabajoExtraccion.Tipo.OFERTA).latest('pk')
        self.oferta.requisitos_obligatorios = 'Python y Django'
        self.oferta.requisitos_estructurados = [{'id': 'req-django', 'category': 'technical_skills',
            'source': 'requisitos_obligatorios', 'name': 'Django', 'mandatory': True, 'exclusionary': False}]
        self.oferta.save(update_fields=['requisitos_obligatorios', 'requisitos_estructurados'])
        job_b, _ = request_offer_extraction(self.oferta)
        job_a.estado = TrabajoExtraccion.Estado.PROCESANDO
        job_a.save(update_fields=['estado'])
        content_b = {**offer_snapshot(self.oferta), 'requirements': self.oferta.requisitos_estructurados}
        receive_extraction_event({
            'event_id': 'current-b', 'request_id': job_b.clave_idempotencia, 'source_hash': job_b.source_hash,
            'job_id': 'remote-b', 'kind': 'job_offer', 'candidate_id': None,
            'analysis_id': None, 'offer_id': self.oferta.pk, 'status': 'completed', 'result': content_b,
        })
        content = {**offer_snapshot(self.oferta), 'requirements': self.oferta.requisitos_estructurados}
        receive_extraction_event({
            'event_id': 'late-a', 'request_id': job_a.clave_idempotencia, 'source_hash': job_a.source_hash,
            'job_id': 'remote-a', 'kind': 'job_offer', 'candidate_id': None,
            'analysis_id': None, 'offer_id': self.oferta.pk, 'status': 'completed', 'result': content,
        })
        job_b.refresh_from_db()
        self.assertEqual(job_b.estado, TrabajoExtraccion.Estado.COMPLETADO)
        self.offer_profile.refresh_from_db()
        expected_profile_hash = self.offer_profile.source_hash
        self.assertNotEqual(expected_profile_hash, 'c' * 64)
        match, created = get_or_create_match(self.postulante, self.oferta)
        self.assertTrue(created)
        self.assertEqual(match.perfil_oferta_hash, expected_profile_hash)


class CompatibilityConfigurationTests(TestCase):
    def test_borrador_no_publica_sin_100_y_preserva_valores(self):
        user = Usuario.objects.create_superuser(email='admin@example.com', password='test-password')
        config = ConfiguracionCompatibilidad.objects.create(
            version='borrador-uno', technical_skills=Decimal('20.00'), soft_skills=Decimal('15.00'),
            experience=Decimal('20.00'), education=Decimal('10.00'), languages=Decimal('5.00'),
            logistics=Decimal('5.00'), desirables=Decimal('10.00'),
        )
        with self.assertRaises(ValidationError):
            publish_configuration(config.pk, user)
        config.refresh_from_db()
        self.assertTrue(config.es_borrador)
        self.assertEqual(config.technical_skills, Decimal('20.00'))

    def test_publicada_es_inmutable_y_admin_no_puede_borrarla(self):
        user = Usuario.objects.create_superuser(email='admin@example.com', password='test-password')
        config = ConfiguracionCompatibilidad.objects.get(version='rubrica-inicial-v1')
        with self.assertRaises(ValidationError):
            config.delete()
        with self.assertRaises(ValidationError):
            config.technical_skills = Decimal('34.00')
            config.save()


class MatchConsumerTransactionTests(TransactionTestCase):
    def test_websocket_carga_configuracion_antes_de_serializar_payload(self):
        # Channels closes old DB connections at the sync/async boundary. Its
        # query must observe committed fixtures rather than TestCase's atomic.
        from .consumers import MatchConsumer

        user = Usuario.objects.create_user(email='socket@example.com', password='synthetic-password')
        postulante = Postulante.objects.create(usuario=user)
        category = Categoria.objects.create(nombre='Synthetic category')
        offer = Oferta.objects.create(
            empresa=user, categoria=category, titulo='Synthetic role', nombre_puesto='Synthetic role',
            ubicacion='Synthetic location', descripcion='Synthetic role', habilidades_requeridas='',
            nivel_educativo='secundario', fecha_cierre=timezone.now() + timedelta(days=1),
        )
        config = ConfiguracionCompatibilidad.objects.create(version='socket-fixture', es_borrador=False)
        match = ResultadoCompatibilidad.objects.create(
            postulante=postulante, oferta=offer, cache_key='a' * 64,
            perfil_cv_version=1, perfil_oferta_version=1,
            perfil_cv_hash='b' * 64, perfil_oferta_hash='c' * 64,
            configuracion=config, scoring_weights=config.pesos_basis_points(),
        )
        loaded = async_to_sync(MatchConsumer().owned_match)(user.pk, match.request_id)
        self.assertEqual(status_payload(loaded)['scoring_config']['version'], config.version)
