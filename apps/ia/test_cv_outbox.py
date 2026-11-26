import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from ia.cv_outbox import ensure_cv_dispatch_event
from ia.models import EventoSalida, TrabajoExtraccion, private_cv_storage
from ia.workflow import request_cv_extraction
from usuarios.models import Usuario, Postulante
from usuarios.services import cargar_cv


class CVOutboxRecoveryTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        storage = patch.object(private_cv_storage, 'location', self.directory.name)
        storage.start()
        self.addCleanup(storage.stop)
        user = Usuario.objects.create_user(email='outbox-recovery@example.invalid', password='synthetic-test-password')
        self.candidate = Postulante.objects.create(usuario=user)
        cargar_cv(self.candidate, SimpleUploadedFile('cv.txt', b'Python developer with documented experience.'))
        self.candidate.refresh_from_db()

    def tearDown(self):
        for version in self.candidate.versiones_cv.all():
            version.archivo.delete(save=False)
        super().tearDown()

    def test_deleted_job_event_cannot_swallow_new_analysis(self):
        analysis, old_job, _ = request_cv_extraction(self.candidate)
        old_key = old_job.clave_idempotencia
        old_id = old_job.pk
        # Reproduce the legacy key left behind by historical data cleanup.
        legacy = EventoSalida.objects.create(
            clave_idempotencia=f'outbox:{old_key}', tipo=EventoSalida.Tipo.EXTRAER_CV,
            payload={'job_id': old_id}, estado=EventoSalida.Estado.ERROR, error='Historical orphan.',
        )
        old_job.delete()
        job = TrabajoExtraccion.objects.create(
            clave_idempotencia=old_key, tipo=TrabajoExtraccion.Tipo.CV,
            analisis_cv=analysis, source_hash=analysis.version_cv.sha256,
            prompt_version=old_job.prompt_version,
        )
        _, resumed, created = request_cv_extraction(self.candidate)
        self.assertFalse(created)
        self.assertEqual(resumed.pk, job.pk)
        event = ensure_cv_dispatch_event(job)
        self.assertEqual(event.payload, {'job_id': job.pk})
        self.assertEqual(event.estado, 'pending')
        self.assertEqual(ensure_cv_dispatch_event(job).pk, event.pk)
        legacy.refresh_from_db()
        self.assertEqual(legacy.payload, {'job_id': old_id})
        self.assertEqual(legacy.error, 'Historical orphan.')
        self.assertEqual(EventoSalida.objects.filter(payload__job_id=job.pk).count(), 1)

    def test_valid_legacy_event_is_reused_even_after_submission(self):
        _, job, _ = request_cv_extraction(self.candidate)
        EventoSalida.objects.filter(payload__job_id=job.pk).delete()
        legacy = EventoSalida.objects.create(
            clave_idempotencia=f'outbox:{job.clave_idempotencia}', tipo=EventoSalida.Tipo.EXTRAER_CV,
            payload={'job_id': job.pk}, estado=EventoSalida.Estado.ENVIADO,
        )
        self.assertEqual(ensure_cv_dispatch_event(job).pk, legacy.pk)
        request_cv_extraction(self.candidate)
        self.assertEqual(EventoSalida.objects.filter(payload__job_id=job.pk).count(), 1)

    def test_repeated_submission_keeps_one_job_and_one_event(self):
        _, first, _ = request_cv_extraction(self.candidate)
        _, second, created = request_cv_extraction(self.candidate)
        self.assertFalse(created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(EventoSalida.objects.filter(payload__job_id=first.pk).count(), 1)
