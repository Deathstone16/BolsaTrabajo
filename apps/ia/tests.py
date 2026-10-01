import hashlib
import hmac
import json
import time

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.models import Postulante, Usuario

from .models import AnalisisCV, EventoSalida, PerfilCV, TrabajoExtraccion
from .workflow import publish_candidate_profile, request_cv_extraction, request_profile_normalization


@override_settings(
    IA_API_URL='http://api-externa.test/api/v1/cv-analyses',
    IA_API_TOKEN='token-de-servicio',
    IA_CALLBACK_TOKEN='token-de-callback',
    IA_CALLBACK_HMAC_SECRET='token-de-callback',
)
class AnalisisCVViewsTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(email='postulante@example.com', password='clave-segura')
        self.postulante = Postulante.objects.create(
            usuario=self.usuario,
            cv=SimpleUploadedFile('cv.pdf', b'%PDF-1.4 contenido'),
        )
        self.client.force_login(self.usuario)

    def _result(self):
        return {
            'schema_version': 'candidate-profile.v1',
            'profile_id': str(self.postulante.id),
            'headline': 'Backend developer',
            'summary': 'Python developer.',
            'skills': [{'name': 'Python', 'level': 'intermediate', 'evidence': ['Resume skills section']}],
            'work_experience': [], 'education': [], 'languages': [],
            'preferences': {'locations': [], 'work_modes': []},
        }

    def _callback(self, job, status='completed', result=None, error=None):
        payload = {
            'event_id': f'event-{job.pk}-{status}',
            'job_id': 'remote-job-1',
            'request_id': job.clave_idempotencia,
            'analysis_id': job.analisis_cv_id,
            'candidate_id': self.postulante.id,
            'offer_id': None,
            'kind': 'candidate_cv',
            'source_hash': job.source_hash,
            'status': status,
            'result': result,
            'error': error,
        }
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
        self.assertEqual(job.estado, TrabajoExtraccion.Estado.PENDIENTE)
        self.assertTrue(job.cv_snapshot.name)
        self.assertTrue(EventoSalida.objects.filter(payload__job_id=job.id).exists())

    def test_reutiliza_analisis_pendiente(self):
        analysis, job, _ = request_cv_extraction(self.postulante)
        response = self.client.post(reverse('ia:solicitar_analisis'))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()['analisis_id'], analysis.id)
        self.assertEqual(TrabajoExtraccion.objects.filter(analisis_cv=analysis).count(), 1)

    def test_nuevo_cv_se_habilita_cuando_anterior_termino(self):
        AnalisisCV.objects.create(postulante=self.postulante, estado=AnalisisCV.Estado.COMPLETADO)
        response = self.client.post(reverse('ia:solicitar_analisis'))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(AnalisisCV.objects.filter(postulante=self.postulante, estado=AnalisisCV.Estado.PENDIENTE).count(), 1)

    def test_base_de_datos_impide_dos_analisis_pendientes(self):
        AnalisisCV.objects.create(postulante=self.postulante)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AnalisisCV.objects.create(postulante=self.postulante)

    def test_callback_firmado_guarda_perfil_canonico(self):
        _, job, _ = request_cv_extraction(self.postulante)
        response = self._callback(job, result=self._result())
        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        profile = PerfilCV.objects.get(postulante=self.postulante)
        self.assertEqual(job.estado, TrabajoExtraccion.Estado.COMPLETADO)
        self.assertEqual(profile.version, 1)
        self.assertEqual(profile.contenido['schema_version'], 'candidate-profile.v1')

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
