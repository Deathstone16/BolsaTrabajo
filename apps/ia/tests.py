import asyncio
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone
from categorias.models import Categoria
from ofertas.models import Oferta
from .matching import comparar_oferta_con_analisis
import hashlib
import hmac
import json
import time

from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.models import Postulante, Usuario

from .models import AnalisisCV, ComparacionOfertaCV, EventoSalida, PerfilCV, TrabajoExtraccion, private_cv_storage
from .workflow import CV_PROMPT_VERSION, publish_candidate_profile, request_cv_extraction, request_profile_normalization
from .consumers import CVAnalysisConsumer, TOKEN_SALT
from .profile_skills import split_profile_skills


@override_settings(
    CV_SCAN_ENABLED=False,
    CV_LEGACY_CONVERTER_IMAGE='',
    IA_API_URL='http://api-externa.test/api/v1/cv-analyses',
    IA_API_TOKEN='token-de-servicio',
    IA_CALLBACK_TOKEN='token-de-callback',
    IA_CALLBACK_HMAC_SECRET='token-de-callback',
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
)
class AnalisisCVViewsTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(email='postulante@example.com', password='clave-segura')
        self.postulante = Postulante.objects.create(usuario=self.usuario)
        from usuarios.services import cargar_cv
        cargar_cv(self.postulante, SimpleUploadedFile('cv.txt', b'Perfil profesional\nPython developer with documented experience.'))
        self.postulante.refresh_from_db()
        self.client.force_login(self.usuario)

    def tearDown(self):
        for version in self.postulante.versiones_cv.all():
            version.archivo.delete(save=False)
        super().tearDown()

    def _result(self):
        return {
            'schema_version': 'candidate-profile.v2',
            'profile_id': str(self.postulante.id),
            'headline': 'Backend developer',
            'summary': 'Python developer.',
            'skills': [{'name': 'Python', 'level': 'intermediate', 'evidence': ['Resume skills section'], 'source_quotes': ['Python developer'], 'kind': 'technical', 'origin': 'declared'}],
            'work_experience': [], 'education': [], 'languages': [],
            'preferences': {'locations': [], 'work_modes': []},
        }

    def _callback(self, job, status='completed', result=None, error=None, payload_overrides=None):
        payload = {
            'event_id': f'event-{job.pk}-{status}',
            'job_id': 'remote-job-1',
            'request_id': job.clave_idempotencia,
            'analysis_id': job.analisis_cv_id,
            'cv_version_id': job.analisis_cv.version_cv_id if job.analisis_cv_id else job.source_cv_version_id,
            'candidate_id': (job.analisis_cv.postulante_id if job.analisis_cv_id else job.source_cv_version.postulante_id if job.source_cv_version_id else None),
            'offer_id': None,
            'kind': {
                TrabajoExtraccion.Tipo.CV: 'candidate_cv',
                TrabajoExtraccion.Tipo.OFERTA: 'job_offer',
                TrabajoExtraccion.Tipo.NORMALIZAR_PERFIL: 'profile_normalization',
            }[job.tipo],
            'source_hash': job.source_hash,
            'status': status,
            'result': result,
            'error': error,
        }
        payload.update(payload_overrides or {})
        body = json.dumps(payload).encode('utf-8')
        timestamp = str(int(time.time()))
        signature = hmac.new(
            b'token-de-callback', timestamp.encode('ascii') + b'.' + body, hashlib.sha256
        ).hexdigest()
        return self.client.post(
            reverse('ia:llegue'), data=body, content_type='application/json',
            headers={'X-IA-Event-Timestamp': timestamp, 'X-IA-Callback-Signature': signature},
        )

    def test_crea_trabajo_y_outbox_sin_llamada_http(self):
        response = self.client.post(reverse('ia:solicitar_analisis'))
        self.assertEqual(response.status_code, 202)
        analysis = AnalisisCV.objects.get(postulante=self.postulante)
        job = TrabajoExtraccion.objects.get(analisis_cv=analysis)
        self.assertEqual(job.prompt_version, CV_PROMPT_VERSION)
        self.assertEqual(job.estado, TrabajoExtraccion.Estado.PENDIENTE)
        self.assertTrue(job.cv_snapshot.name)
        self.assertTrue(EventoSalida.objects.filter(payload__job_id=job.id).exists())

    def test_cv_completado_con_prompt_previo_no_se_reutiliza_en_v2_packets(self):
        old_analysis, old_job, _ = request_cv_extraction(self.postulante)
        old_analysis.estado = AnalisisCV.Estado.COMPLETADO
        old_analysis.save(update_fields=['estado'])
        old_job.prompt_version = 'cv-extraction.v2-blocks-refs'
        old_job.clave_idempotencia = f'candidate-cv:{self.postulante.cv_version_actual_id}:{self.postulante.cv_version_actual.sha256}:cv-extraction.v2-blocks-refs'
        old_job.estado = TrabajoExtraccion.Estado.COMPLETADO
        old_job.save(update_fields=['prompt_version', 'clave_idempotencia', 'estado'])

        new_analysis, new_job, created = request_cv_extraction(self.postulante)

        self.assertTrue(created)
        self.assertNotEqual(new_analysis.pk, old_analysis.pk)
        self.assertNotEqual(new_job.pk, old_job.pk)
        self.assertEqual(new_job.prompt_version, CV_PROMPT_VERSION)
        self.assertEqual(AnalisisCV.objects.filter(version_cv=self.postulante.cv_version_actual).count(), 2)

        new_analysis.estado = AnalisisCV.Estado.COMPLETADO
        new_analysis.save(update_fields=['estado'])
        new_job.estado = TrabajoExtraccion.Estado.COMPLETADO
        new_job.save(update_fields=['estado'])
        reused_analysis, reused_job, reused = request_cv_extraction(self.postulante)
        self.assertFalse(reused)
        self.assertEqual(reused_analysis.pk, new_analysis.pk)
        self.assertEqual(reused_job.pk, new_job.pk)

    def test_estado_muestra_mensaje_generico_de_analisis(self):
        analysis, _, _ = request_cv_extraction(self.postulante)
        response = self.client.get(reverse('ia:estado_analisis', args=[analysis.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['mensaje'],
            'Puede tardar varios minutos según la disponibilidad del servicio.',
        )

    def test_comando_migra_snapshot_historico_y_borra_origen_despues_del_commit(self):
        from usuarios.management.commands.migrar_cv_privados import Command

        _, job, _ = request_cv_extraction(self.postulante)
        private_original = job.cv_snapshot.name
        legacy_name = default_storage.save(
            f'ia/extraction_snapshots/test-{job.pk}-{time.time_ns()}.txt',
            ContentFile(b'Perfil profesional historico\nPython developer.'),
        )
        job.cv_snapshot.name = legacy_name
        job.save(update_fields=['cv_snapshot'])
        self.addCleanup(lambda: private_cv_storage.delete(private_original))
        self.addCleanup(lambda: default_storage.delete(legacy_name))

        with self.captureOnCommitCallbacks(execute=True):
            Command()._migrate_snapshot(job.pk)

        job.refresh_from_db()
        migrated_name = job.cv_snapshot.name
        self.addCleanup(lambda: private_cv_storage.delete(migrated_name))
        self.assertTrue(migrated_name.startswith('snapshots/legacy-'))
        self.assertTrue(private_cv_storage.exists(migrated_name))
        with private_cv_storage.open(migrated_name, 'rb') as migrated:
            self.assertEqual(migrated.read(), b'Perfil profesional historico\nPython developer.')
        self.assertFalse(default_storage.exists(legacy_name))

        Command()._migrate_snapshot(job.pk)
        job.refresh_from_db()
        self.assertEqual(job.cv_snapshot.name, migrated_name)

    def test_reutiliza_analisis_pendiente(self):
        analysis, job, _ = request_cv_extraction(self.postulante)
        response = self.client.post(reverse('ia:solicitar_analisis'))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()['analisis_id'], analysis.id)
        self.assertEqual(TrabajoExtraccion.objects.filter(analisis_cv=analysis).count(), 1)

    def test_nuevo_cv_se_habilita_cuando_anterior_termino(self):
        AnalisisCV.objects.create(postulante=self.postulante, version_cv=self.postulante.cv_version_actual, estado=AnalisisCV.Estado.COMPLETADO)
        from usuarios.services import cargar_cv
        cargar_cv(self.postulante, SimpleUploadedFile('cv-v2.txt', b'New resume version with experience.'))
        response = self.client.post(reverse('ia:solicitar_analisis'))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(AnalisisCV.objects.filter(postulante=self.postulante, estado=AnalisisCV.Estado.PENDIENTE).count(), 1)

    def test_historial_permite_varios_analisis_pendientes_por_postulante(self):
        AnalisisCV.objects.create(postulante=self.postulante, version_cv=self.postulante.cv_version_actual)
        AnalisisCV.objects.create(postulante=self.postulante, version_cv=self.postulante.cv_version_actual)
        self.assertEqual(AnalisisCV.objects.filter(postulante=self.postulante).count(), 2)

    def test_callback_firmado_guarda_perfil_canonico(self):
        _, job, _ = request_cv_extraction(self.postulante)
        response = self._callback(job, result=self._result())
        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        profile = PerfilCV.objects.get(postulante=self.postulante)
        self.assertEqual(job.estado, TrabajoExtraccion.Estado.COMPLETADO)
        self.assertEqual(profile.version, 1)
        self.assertEqual(profile.contenido['schema_version'], 'candidate-profile.v2')

    def test_dos_cv_de_postulantes_distintos_conservan_sus_perfiles_aislados(self):
        otro_usuario = Usuario.objects.create_user(email='otro-postulante@example.com', password='clave-segura')
        otro_postulante = Postulante.objects.create(usuario=otro_usuario)
        from usuarios.services import cargar_cv
        otra_version = cargar_cv(
            otro_postulante,
            SimpleUploadedFile('otro-cv.txt', b'Experiencia en soldadura y mantenimiento industrial.'),
        )
        self.addCleanup(lambda: otra_version.archivo.delete(save=False))

        _, job_a, _ = request_cv_extraction(self.postulante)
        _, job_b, _ = request_cv_extraction(otro_postulante)
        result_a = self._result()
        result_a['summary'] = 'Perfil A: experiencia en Python.'
        result_b = self._result()
        result_b['profile_id'] = str(otro_postulante.pk)
        result_b['summary'] = 'Perfil B: experiencia en soldadura.'

        self.assertNotEqual(job_a.clave_idempotencia, job_b.clave_idempotencia)
        self.assertNotEqual(job_a.source_hash, job_b.source_hash)
        self.assertEqual(self._callback(job_b, result=result_b).status_code, 200)
        self.assertEqual(self._callback(job_a, result=result_a).status_code, 200)

        self.assertEqual(PerfilCV.objects.get(postulante=self.postulante).contenido['summary'], result_a['summary'])
        self.assertEqual(PerfilCV.objects.get(postulante=otro_postulante).contenido['summary'], result_b['summary'])
        job_a.refresh_from_db()
        job_b.refresh_from_db()
        self.assertEqual(job_a.analisis_cv.respuesta['result']['profile_id'], str(self.postulante.pk))
        self.assertEqual(job_b.analisis_cv.respuesta['result']['profile_id'], str(otro_postulante.pk))

    def test_callback_rechaza_ids_de_otro_postulante_analisis_cv_o_source_hash(self):
        _, job, _ = request_cv_extraction(self.postulante)
        otro_usuario = Usuario.objects.create_user(email='otro-id@example.com', password='clave-segura')
        otro_postulante = Postulante.objects.create(usuario=otro_usuario)
        casos_invalidos = [
            {'candidate_id': otro_postulante.pk},
            {'candidate_id': True},
            {'analysis_id': True},
            {'cv_version_id': True},
            {'analysis_id': job.analisis_cv_id + 1000},
            {'cv_version_id': job.analisis_cv.version_cv_id + 1000},
            {'source_hash': 'f' * 64},
        ]

        for indice, identidad in enumerate(casos_invalidos):
            with self.subTest(identidad=identidad):
                response = self._callback(
                    job,
                    result=self._result(),
                    payload_overrides={**identidad, 'event_id': f'invalid-identity-{job.pk}-{indice}'},
                )
                self.assertEqual(response.status_code, 404)

        job.refresh_from_db()
        self.assertEqual(job.estado, TrabajoExtraccion.Estado.PENDIENTE)
        self.assertEqual(job.analisis_cv.estado, AnalisisCV.Estado.PENDIENTE)

    def test_callback_rechaza_resultado_con_profile_id_de_otro_postulante(self):
        analysis, job, _ = request_cv_extraction(self.postulante)
        otro_usuario = Usuario.objects.create_user(email='perfil-ajeno@example.com', password='clave-segura')
        otro_postulante = Postulante.objects.create(usuario=otro_usuario)
        resultado_ajeno = self._result()
        resultado_ajeno['profile_id'] = str(otro_postulante.pk)

        response = self._callback(job, result=resultado_ajeno)

        self.assertEqual(response.status_code, 404)
        job.refresh_from_db()
        analysis.refresh_from_db()
        self.assertEqual(job.estado, TrabajoExtraccion.Estado.PENDIENTE)
        self.assertEqual(analysis.estado, AnalisisCV.Estado.PENDIENTE)
        self.assertIsNone(analysis.respuesta)
        self.assertIsNone(analysis.perfil_snapshot)
        self.assertFalse(PerfilCV.objects.filter(postulante=otro_postulante).exists())
        self.assertIsNone(PerfilCV.objects.get(postulante=self.postulante).contenido)

    def test_callback_duplicado_es_idempotente(self):
        _, job, _ = request_cv_extraction(self.postulante)
        self.assertEqual(self._callback(job, result=self._result()).status_code, 200)
        duplicate = self._callback(job, result=self._result())
        self.assertEqual(duplicate.status_code, 200)
        self.assertTrue(duplicate.json()['duplicado'])
        self.assertEqual(PerfilCV.objects.get(postulante=self.postulante).version, 1)

    def test_callback_error_marca_analisis(self):
        analysis, job, _ = request_cv_extraction(self.postulante)
        response = self._callback(job, status='failed', error='PDF could not be read.')
        self.assertEqual(response.status_code, 200)
        analysis.refresh_from_db()
        self.assertEqual(analysis.estado, AnalisisCV.Estado.ERROR)

    def test_reintento_tras_error_y_doble_post_reutilizan_el_mismo_job(self):
        _, failed_job, _ = request_cv_extraction(self.postulante)
        self._callback(failed_job, status='failed', error='Falló la extracción.')
        analysis_retry, retry_job, created = request_cv_extraction(self.postulante)
        analysis_again, same_job, created_again = request_cv_extraction(self.postulante)
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(analysis_retry.pk, analysis_again.pk)
        self.assertEqual(retry_job.pk, same_job.pk)

    @patch('ia.management.commands.dispatch_integration_outbox.requests.post')
    def test_dispatch_cv_envia_la_identidad_de_version_inmutable(self, post):
        from ia.management.commands.dispatch_integration_outbox import Command
        _, job, _ = request_cv_extraction(self.postulante)
        event = EventoSalida.objects.get(payload__job_id=job.pk)
        response = post.return_value
        response.json.return_value = {'job_id': 'remote-cv-packet-job'}

        Command()._dispatch(event)

        self.assertEqual(post.call_args.kwargs['data']['analysis_id'], job.analisis_cv_id)
        self.assertEqual(post.call_args.kwargs['data']['candidate_id'], self.postulante.pk)
        self.assertEqual(post.call_args.kwargs['data']['cv_version_id'], job.analisis_cv.version_cv_id)

    def test_trabajo_enviando_vencido_se_recupera_por_el_dispatcher(self):
        from datetime import timedelta
        from django.utils import timezone
        from ia.management.commands.dispatch_integration_outbox import Command
        _, job, _ = request_cv_extraction(self.postulante)
        event = EventoSalida.objects.get(payload__job_id=job.pk)
        command = Command()
        claimed = command._claim_next()
        self.assertEqual(claimed.pk, event.pk)
        EventoSalida.objects.filter(pk=event.pk).update(actualizado_en=timezone.now() - timedelta(minutes=10))
        reclaimed = command._claim_next()
        self.assertEqual(reclaimed.pk, event.pk)

    def test_respuestas_de_versiones_cv_no_mezclan_perfil_y_la_version_vieja_no_publica(self):
        from usuarios.services import cargar_cv
        _, job_a, _ = request_cv_extraction(self.postulante)
        version_a_id = job_a.analisis_cv.version_cv_id
        version_b = cargar_cv(self.postulante, SimpleUploadedFile('cv-b.txt', b'Other resume content.'))
        _, job_b, _ = request_cv_extraction(self.postulante)
        self.assertNotEqual(job_a.source_hash, job_b.source_hash)

        result_b = self._result()
        result_b['summary'] = 'Perfil de la versión B.'
        result_a = self._result()
        result_a['summary'] = 'Perfil histórico de la versión A.'
        self.assertEqual(self._callback(job_b, result=result_b).status_code, 200)
        self.assertEqual(self._callback(job_a, result=result_a).status_code, 200)

        self.postulante.refresh_from_db()
        profile = PerfilCV.objects.get(postulante=self.postulante)
        analysis_a = AnalisisCV.objects.get(version_cv_id=version_a_id)
        analysis_b = AnalisisCV.objects.get(version_cv=version_b)
        self.assertEqual(self.postulante.cv_version_actual_id, version_b.pk)
        self.assertEqual(analysis_a.estado, AnalisisCV.Estado.COMPLETADO)
        self.assertEqual(analysis_b.estado, AnalisisCV.Estado.COMPLETADO)
        self.assertEqual(analysis_a.respuesta['result']['summary'], result_a['summary'])
        self.assertEqual(analysis_b.respuesta['result']['summary'], result_b['summary'])
        self.assertEqual(profile.cv_version_id, version_b.pk)
        self.assertEqual(profile.contenido['summary'], result_b['summary'])
        status = self.client.get(reverse('ia:estado_analisis', args=[analysis_a.pk])).json()
        self.assertFalse(status['es_version_actual'])
        self.assertIsNone(status['resultado_url'])
        self.assertIn('versión anterior', status['mensaje'])

    def test_resultado_historico_solo_es_visible_para_su_dueno(self):
        _, job, _ = request_cv_extraction(self.postulante)
        self.assertEqual(self._callback(job, result=self._result()).status_code, 200)
        analysis = job.analisis_cv
        self.assertEqual(self.client.get(reverse('ia:ver_resultado', args=[analysis.pk])).status_code, 200)
        other_user = Usuario.objects.create_user(email='otro@example.com', password='clave-segura')
        Postulante.objects.create(usuario=other_user)
        self.client.force_login(other_user)
        self.assertEqual(self.client.get(reverse('ia:ver_resultado', args=[analysis.pk])).status_code, 404)

    def test_perfil_profesional_muestra_la_version_editada_que_usa_el_match(self):
        original = self._result()
        analysis = AnalisisCV.objects.create(
            postulante=self.postulante,
            version_cv=self.postulante.cv_version_actual,
            estado=AnalisisCV.Estado.COMPLETADO,
            perfil_snapshot=original,
        )
        publish_candidate_profile(self.postulante, original, 'a' * 64, 'extraction', analysis)
        edited = self._result()
        edited['summary'] = 'Perfil final actualizado por la postulante.'
        edited['skills'].append({
            'name': 'PostgreSQL', 'level': 'intermediate', 'kind': 'technical',
            'origin': 'user_declared', 'evidence': ['Declarada directamente por la postulante'],
        })
        edited['work_experience'] = [{
            'job_title': 'Analista de datos', 'organization': 'Empresa de prueba',
            'duration_months': 12, 'highlights': ['Preparó informes'],
        }]
        edited['languages'] = [{'name': 'Inglés', 'level': 'professional'}]
        edited['preferences'] = {'locations': ['Resistencia'], 'work_modes': ['remote']}
        publish_candidate_profile(self.postulante, edited, 'b' * 64, 'user_edit')

        profile_url = reverse('ia:perfil_profesional')
        page = self.client.get(profile_url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'Perfil final actualizado por la postulante.')
        for expected in ('PostgreSQL', 'Analista de datos', 'Preparó informes', 'Inglés', 'Resistencia', 'Remoto'):
            self.assertContains(page, expected)
        self.assertContains(page, 'Versión 2')
        self.assertContains(page, 'Editar información')
        self.assertContains(self.client.get(reverse('mi_perfil')), f'href="{profile_url}"')
        self.assertNotContains(self.client.get(reverse('ia:ver_resultado', args=[analysis.pk])), 'PostgreSQL')

    def test_perfil_profesional_no_muestra_un_cv_anterior_ni_datos_ajenos(self):
        profile = publish_candidate_profile(self.postulante, self._result(), 'a' * 64, 'extraction')
        profile.estado = 'processing'
        profile.save(update_fields=['estado'])
        processing = self.client.get(reverse('ia:perfil_profesional'))
        self.assertContains(processing, 'Estamos actualizando tu perfil')
        self.assertNotContains(processing, 'Python developer.')

        profile.estado = 'ready'
        profile.cv_version = None
        profile.save(update_fields=['estado', 'cv_version'])
        stale = self.client.get(reverse('ia:perfil_profesional'))
        self.assertContains(stale, 'Todavía no hay un perfil listo')
        self.assertNotContains(stale, 'Python developer.')

        other_user = Usuario.objects.create_user(email='otro-perfil@example.com', password='clave-segura')
        Postulante.objects.create(usuario=other_user)
        self.client.force_login(other_user)
        other = self.client.get(reverse('ia:perfil_profesional'))
        self.assertEqual(other.status_code, 200)
        self.assertNotContains(other, 'Python developer.')

    def test_guardar_edicion_lleva_al_perfil_profesional_en_proceso(self):
        profile = publish_candidate_profile(self.postulante, self._result(), 'a' * 64, 'extraction')
        response = self.client.post(reverse('ia:editar_perfil_cv'), {
            'version': profile.version,
            'headline': 'Backend developer',
            'summary': 'Resumen editado por la postulante.',
            'skills': 'Python',
            'languages': '',
            'locations': '',
        })
        self.assertRedirects(response, reverse('ia:perfil_profesional'), fetch_redirect_response=False)
        profile.refresh_from_db()
        self.assertEqual(profile.estado, 'processing')

    def test_edicion_se_normaliza_antes_de_reemplazar_el_perfil_canonico(self):
        profile = publish_candidate_profile(
            self.postulante, self._result(), 'a' * 64, 'extraction'
        )
        edited = dict(profile.contenido)
        edited['summary'] = 'Desarrolladora Python con experiencia en APIs.'

        job, created = request_profile_normalization(self.postulante, edited, profile.version)

        self.assertTrue(created)
        profile.refresh_from_db()
        self.assertEqual(profile.estado, 'processing')
        self.assertEqual(job.tipo, TrabajoExtraccion.Tipo.NORMALIZAR_PERFIL)
        self.assertTrue(EventoSalida.objects.filter(payload__job_id=job.id).exists())

        normalized = self._result()
        normalized['summary'] = 'Python developer with API experience.'
        self.assertEqual(self._callback(job, result=normalized).status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.estado, 'ready')
        self.assertEqual(profile.origen, 'user_edit')
        self.assertEqual(profile.contenido['summary'], normalized['summary'])

    def test_edicion_conserva_origen_citas_y_rechazos_de_habilidades(self):
        from ia.forms import PerfilCVForm
        profile = publish_candidate_profile(self.postulante, self._result(), 'a' * 64, 'extraction')
        form = PerfilCVForm(data={
            'version': profile.version, 'headline': 'Backend', 'summary': '',
            'skills': 'Teamwork, Manual testing', 'languages': '', 'locations': '',
        })
        self.assertTrue(form.is_valid(), form.errors)
        edited = form.apply_to(profile.contenido)
        self.assertEqual(edited['skills'][0]['origin'], 'user_declared')
        self.assertTrue(edited['skills'][0]['evidence'])
        self.assertEqual(edited['skills'][1]['origin'], 'user_declared')
        self.assertEqual(edited['rejected_skills'][0]['name'], 'Python')

    def test_cv_nuevo_reemplaza_perfil_editado_al_completar(self):
        profile = publish_candidate_profile(
            self.postulante, self._result(), 'a' * 64, 'extraction'
        )
        profile.origen = 'user_edit'
        profile.save(update_fields=['origen', 'actualizado_en'])

        _, job, _ = request_cv_extraction(self.postulante)
        replacement = self._result()
        replacement['summary'] = 'New resume profile from the latest CV.'
        response = self._callback(job, result=replacement)

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.origen, 'extraction')
        self.assertEqual(profile.contenido['summary'], replacement['summary'])

    def test_perfil_y_resultado_muestran_habilidades_blandas_separadas(self):
        analysis = AnalisisCV.objects.create(
            postulante=self.postulante, estado=AnalisisCV.Estado.COMPLETADO,
        )
        result = self._result()
        result['skills'] += [
            {'name': 'Analytical Thinking', 'level': 'unknown', 'evidence': ['Explicitly stated in CV'], 'source_quotes': ['Analytical Thinking'], 'kind': 'soft', 'origin': 'declared'},
            {'name': 'Teamwork', 'level': 'unknown', 'evidence': ['Explicitly stated in CV'], 'source_quotes': ['Teamwork'], 'kind': 'soft', 'origin': 'declared'},
            {'name': 'Orientación al cliente', 'level': 'unknown', 'evidence': ['Adaptó la solución a las necesidades del cliente'], 'source_quotes': ['Adapté la solución a las necesidades del cliente'], 'kind': 'soft', 'origin': 'inferred'},
        ]
        analysis.version_cv = self.postulante.cv_version_actual
        analysis.perfil_snapshot = result
        analysis.save(update_fields=['version_cv', 'perfil_snapshot'])
        publish_candidate_profile(self.postulante, result, 'a' * 64, 'extraction', analysis)

        hard, soft = split_profile_skills(result)
        self.assertEqual([skill['name'] for skill in hard], ['Python'])
        self.assertEqual([skill['name'] for skill in soft], ['Analytical Thinking', 'Teamwork', 'Orientación al cliente'])

        detail = self.client.get(reverse('ia:ver_resultado', args=[analysis.pk]))
        profile_page = self.client.get(reverse('mi_perfil'))
        self.assertContains(detail, 'id="habilidades-blandas-cv"')
        self.assertContains(detail, 'Teamwork')
        self.assertContains(profile_page, 'id="habilidades-blandas-perfil"')
        self.assertContains(profile_page, 'Analytical Thinking')
        self.assertContains(profile_page, 'Orientación al cliente')
        self.assertNotContains(profile_page, 'Inferida')
        self.assertNotContains(detail, 'Inferida a partir de las tareas descritas')
        self.assertNotContains(detail, 'Declarada en el CV')
        self.assertNotContains(detail, 'Ver evidencia del CV')
        self.assertNotContains(detail, 'Adapté la solución a las necesidades del cliente')
        self.assertContains(detail, 'Adaptó la solución a las necesidades del cliente')


    def test_resultado_de_oficios_oculta_nivel_desconocido_y_traduce_niveles(self):
        result = self._result()
        result['skills'] = [
            {'name': name, 'level': level, 'kind': 'technical', 'origin': 'declared'}
            for name, level in (
                ('Manipulación de alimentos', 'unknown'),
                ('Control de inventario', 'beginner'),
                ('Operación de maquinaria', 'intermediate'),
                ('Seguridad e higiene', 'advanced'),
                ('Mantenimiento industrial', 'expert'),
            )
        ]
        analysis = AnalisisCV.objects.create(
            postulante=self.postulante, estado=AnalisisCV.Estado.COMPLETADO,
            version_cv=self.postulante.cv_version_actual, perfil_snapshot=result,
        )

        detail = self.client.get(reverse('ia:ver_resultado', args=[analysis.pk]))

        self.assertEqual(detail.status_code, 200)
        for name in (skill['name'] for skill in result['skills']):
            self.assertContains(detail, name)
        for label in ('Principiante', 'Intermedio', 'Avanzado', 'Experto'):
            self.assertContains(detail, f'>{label}</span>', html=False)
        self.assertNotContains(detail, 'unknown')
        self.assertNotContains(detail, 'chip shrink-0"></span>')
        analysis.refresh_from_db()
        self.assertEqual(analysis.perfil_snapshot['skills'][0]['level'], 'unknown')

    def test_postulante_guarda_todas_las_habilidades_sin_perder_sugerencia_ia(self):
        analisis = AnalisisCV.objects.create(
            postulante=self.postulante,
            estado=AnalisisCV.Estado.COMPLETADO,
            respuesta={'result': {'habilidades_analizadas': [
                {'tecnologia': 'Python', 'nivel_evaluado': 'Principiante'},
                {'tecnologia': 'Django', 'nivel_evaluado': 'Intermedio'},
            ]}},
        )
        resultado_url = reverse('ia:ver_resultado', args=[analisis.id])
        editar_url = reverse('ia:editar_habilidades', args=[analisis.id])

        self.assertContains(self.client.get(resultado_url), editar_url)
        self.assertNotContains(self.client.get(resultado_url), 'name="nivel_0"')
        self.assertContains(self.client.get(editar_url), 'name="nivel_0"')
        response = self.client.post(
            editar_url,
            {'opinion_0': 'no', 'nivel_0': 'Avanzado', 'opinion_1': 'si', 'nivel_1': 'Intermedio'},
        )

        self.assertRedirects(response, resultado_url)
        analisis.refresh_from_db()
        primera, segunda = analisis.respuesta['result']['habilidades_analizadas']
        self.assertEqual(primera['nivel_evaluado'], 'Principiante')
        self.assertEqual(primera['nivel_usuario'], 'Avanzado')
        self.assertEqual(primera['acuerdo_usuario'], 'no')
        self.assertEqual(segunda['nivel_usuario'], 'Intermedio')
        self.assertEqual(segunda['acuerdo_usuario'], 'si')

    def test_no_se_puede_editar_analisis_ajeno_ni_nivel_invalido(self):
        otro_usuario = Usuario.objects.create_user(email='otro@example.com', password='clave-segura')
        otro_postulante = Postulante.objects.create(usuario=otro_usuario)
        analisis = AnalisisCV.objects.create(
            postulante=otro_postulante,
            estado=AnalisisCV.Estado.COMPLETADO,
            respuesta={'result': {'habilidades_analizadas': [
                {'tecnologia': 'Python', 'nivel_evaluado': 'Principiante'},
            ]}},
        )
        url = reverse('ia:editar_habilidades', args=[analisis.id])

        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(otro_usuario)
        self.assertEqual(self.client.post(url, {'opinion_0': 'si', 'nivel_0': 'Experto'}).status_code, 400)

    def test_nivel_invalido_no_guarda_ninguna_habilidad(self):
        analisis = AnalisisCV.objects.create(
            postulante=self.postulante,
            estado=AnalisisCV.Estado.COMPLETADO,
            respuesta={'result': {'habilidades_analizadas': [
                {'tecnologia': 'Python', 'nivel_evaluado': 'Principiante'},
                {'tecnologia': 'Django', 'nivel_evaluado': 'Intermedio'},
            ]}},
        )

        response = self.client.post(
            reverse('ia:editar_habilidades', args=[analisis.id]),
            {'opinion_0': 'no', 'nivel_0': 'Avanzado', 'opinion_1': 'si', 'nivel_1': 'Experto'},
        )

        self.assertEqual(response.status_code, 400)
        analisis.refresh_from_db()
        self.assertNotIn('nivel_usuario', analisis.respuesta['result']['habilidades_analizadas'][0])

@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class CVAnalysisConsumerTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(email='ws@example.com', password='clave-segura')

    def test_consumer_recibe_broadcast_solo_con_token_del_usuario(self):
        async def scenario():
            token = signing.dumps(self.usuario.pk, salt=TOKEN_SALT)
            socket = WebsocketCommunicator(CVAnalysisConsumer.as_asgi(), f'/ws/cv-analysis/?token={token}')
            socket.scope['user'] = self.usuario
            connected, _ = await socket.connect()
            self.assertTrue(connected)
            await get_channel_layer().group_send(f'user_{self.usuario.pk}', {
                'type': 'cv.analysis.complete',
                'payload': {'analysis_id': 42, 'status': 'completado'},
            })
            self.assertEqual(await socket.receive_json_from(), {
                'type': 'cv.analyzed',
                'payload': {'analysis_id': 42, 'status': 'completado'},
            })
            await socket.disconnect()

            bad = WebsocketCommunicator(CVAnalysisConsumer.as_asgi(), '/ws/cv-analysis/?token=invalid')
            bad.scope['user'] = self.usuario
            connected, _ = await bad.connect()
            self.assertFalse(connected)

        asyncio.run(scenario())


class ComparacionOfertaCVTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email='match@example.com',
            password='clave-segura',
        )
        self.postulante = Postulante.objects.create(usuario=self.usuario)
        self.empresa = Usuario.objects.create_user(
            email='empresa-match@example.com',
            password='clave-segura',
        )
        self.categoria = Categoria.objects.create(nombre='Tecnología')
        self.oferta = Oferta.objects.create(
            empresa=self.empresa,
            categoria=self.categoria,
            titulo='Desarrollador backend',
            nombre_puesto='Backend Developer',
            ubicacion='Resistencia',
            descripcion='Desarrollo de aplicaciones.',
            habilidades_duras='Python, Django, SQL',
            habilidades_blandas='Comunicación',
            habilidades_requeridas='Python, Django, SQL, Comunicación',
            nivel_educativo='universitario',
            estado='activa',
            fecha_cierre=timezone.now() + timedelta(days=10),
        )
        self.analisis = AnalisisCV.objects.create(
            postulante=self.postulante,
            estado=AnalisisCV.Estado.COMPLETADO,
            respuesta={
                'status': 'completed',
                'result': {
                    'habilidades_analizadas': [
                        {'tecnologia': 'Python', 'nivel_evaluado': 'Intermedio'},
                        {'tecnologia': 'Django REST Framework', 'nivel_evaluado': 'Principiante'},
                    ],
                },
            },
        )

    def test_calcula_porcentaje_con_datos_guardados_del_cv(self):
        resultado = comparar_oferta_con_analisis(self.oferta, self.analisis)

        self.assertEqual(resultado['porcentaje'], 50)
        self.assertEqual(
            [item['requisito'] for item in resultado['coincidencias']],
            ['Python', 'Django'],
        )
        self.assertEqual(resultado['habilidades_faltantes'], ['SQL', 'Comunicación'])

    @patch('ia.management.commands.dispatch_integration_outbox.requests.post')
    def test_ruta_legacy_redirige_sin_crear_un_score_historico(self, post):
        self.client.force_login(self.usuario)

        response = self.client.post(reverse('comparar_oferta_cv', args=[self.oferta.pk]))

        self.assertRedirects(response, reverse('detalle_oferta', args=[self.oferta.pk]))
        self.assertFalse(ComparacionOfertaCV.objects.exists())
        post.assert_not_called()

    def test_detalle_no_calcula_match_automaticamente(self):
        self.client.force_login(self.usuario)

        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Comparar con mi CV')
        self.assertFalse(ComparacionOfertaCV.objects.exists())

    def test_ruta_legacy_no_persiste_resultados_con_el_score_antiguo(self):
        self.client.force_login(self.usuario)
        url = reverse('comparar_oferta_cv', args=[self.oferta.pk])

        self.client.post(url)
        self.oferta.habilidades_requeridas = 'Python'
        self.oferta.save(update_fields=['habilidades_requeridas'])
        self.client.post(url)

        self.assertEqual(ComparacionOfertaCV.objects.count(), 0)

    def test_no_usa_analisis_de_un_cv_anterior(self):
        self.postulante.cv_fecha_carga = timezone.now() + timedelta(seconds=1)
        self.postulante.save(update_fields=['cv_fecha_carga'])
        self.client.force_login(self.usuario)

        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))

        self.assertIsNone(response.context['analisis_cv'])
        self.assertContains(response, 'Primero necesitás analizar tu CV')

    def test_no_muestra_comparacion_si_cambiaron_los_requisitos(self):
        self.client.force_login(self.usuario)
        url = reverse('comparar_oferta_cv', args=[self.oferta.pk])
        self.client.post(url)
        self.oferta.habilidades_requeridas = 'Python, Docker'
        self.oferta.save(update_fields=['habilidades_requeridas'])

        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))

        self.assertIsNone(response.context['comparacion'])
        self.assertContains(response, 'Comparar con mi CV')
