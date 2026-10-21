"""Regression cases for immutable CV ownership and extraction recovery."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from categorias.models import Categoria
from ofertas.models import Oferta
from usuarios.models import Postulante, Usuario

from .models import AnalisisCV, CVVersion, EstadoPerfil, PerfilCV, PerfilOferta, TrabajoExtraccion
from .workflow import (
    CV_PROMPT_VERSION,
    publish_candidate_profile,
    publish_offer_profile,
    request_cv_extraction,
    request_profile_normalization,
)


class ExtractionRecoveryTests(TestCase):
    def setUp(self):
        user = Usuario.objects.create_user(email='recovery@example.com', password='synthetic-password')
        self.postulante = Postulante.objects.create(usuario=user)
        self.version = self.make_version(1)
        self.postulante.cv_version_actual = self.version
        self.postulante.save(update_fields=['cv_version_actual'])
        self.content = {
            'schema_version': 'candidate-profile.v2', 'profile_id': str(self.postulante.pk),
            'skills': [], 'work_experience': [], 'education': [], 'languages': [],
            'preferences': {'locations': [], 'work_modes': []},
        }

    def make_version(self, number):
        # These cases only use stored identity, so no real upload is needed.
        return CVVersion.objects.create(
            postulante=self.postulante, numero=number, archivo=f'synthetic-{number}.txt',
            nombre_original='synthetic.txt', sha256=str(number) * 64, formato='txt', tamano=10,
        )

    def test_successful_cv_retry_reuses_its_own_job_and_idempotency_key(self):
        base = f'candidate-cv:{self.version.pk}:{self.version.sha256}:{CV_PROMPT_VERSION}'
        failed = AnalisisCV.objects.create(
            postulante=self.postulante, version_cv=self.version, estado=AnalisisCV.Estado.ERROR,
        )
        TrabajoExtraccion.objects.create(
            analisis_cv=failed, clave_idempotencia=base, source_hash=self.version.sha256,
            tipo=TrabajoExtraccion.Tipo.CV, prompt_version=CV_PROMPT_VERSION,
            estado=TrabajoExtraccion.Estado.ERROR,
        )
        completed = AnalisisCV.objects.create(
            postulante=self.postulante, version_cv=self.version, estado=AnalisisCV.Estado.COMPLETADO,
        )
        retry = TrabajoExtraccion.objects.create(
            analisis_cv=completed, clave_idempotencia=f'{base}:retry:synthetic',
            source_hash=self.version.sha256, tipo=TrabajoExtraccion.Tipo.CV,
            prompt_version=CV_PROMPT_VERSION, estado=TrabajoExtraccion.Estado.COMPLETADO,
        )
        analysis, job, created = request_cv_extraction(self.postulante)
        self.assertEqual(analysis.pk, completed.pk)
        self.assertEqual(job.pk, retry.pk)
        self.assertEqual(job.analisis_cv_id, analysis.pk)
        self.assertFalse(created)

    def test_normalization_reloads_current_cv_instead_of_using_cached_owner(self):
        profile = PerfilCV.objects.create(
            postulante=self.postulante, cv_version=self.version, version=1,
            estado=EstadoPerfil.LISTO, contenido=self.content,
        )
        newer = self.make_version(2)
        Postulante.objects.filter(pk=self.postulante.pk).update(cv_version_actual=newer)
        with self.assertRaisesMessage(ValueError, 'El CV cambió'):
            request_profile_normalization(self.postulante, self.content, profile.version)
        self.assertFalse(TrabajoExtraccion.objects.exists())
        profile.refresh_from_db()
        self.assertEqual(profile.estado, EstadoPerfil.LISTO)

    def test_publication_rejects_candidate_profile_owned_by_another_candidate(self):
        with self.assertRaisesMessage(ValueError, 'no corresponde al postulante'):
            publish_candidate_profile(
                self.postulante, {**self.content, 'profile_id': 'another-candidate'},
                self.version.sha256, 'extraction', cv_version=self.version,
            )
        self.assertFalse(PerfilCV.objects.exists())

    def test_publication_rejects_wrong_offer_owner_and_legacy_schema(self):
        category = Categoria.objects.create(nombre='Synthetic category')
        offer = Oferta.objects.create(
            empresa=self.postulante.usuario, categoria=category, titulo='Synthetic role',
            nombre_puesto='Synthetic role', ubicacion='Synthetic location', descripcion='Synthetic role',
            habilidades_requeridas='', nivel_educativo='secundario',
            fecha_cierre=timezone.now() + timedelta(days=1),
        )
        for content in (
            {'schema_version': 'job-offer.v2', 'offer_id': 'wrong-owner', 'title': 'Synthetic role'},
            {'schema_version': 'job-offer.v1', 'offer_id': str(offer.pk), 'title': 'Synthetic role'},
        ):
            with self.subTest(content=content):
                with self.assertRaisesMessage(ValueError, 'no corresponde a la oferta'):
                    publish_offer_profile(offer, content, 'a' * 64)
        self.assertFalse(PerfilOferta.objects.exists())
