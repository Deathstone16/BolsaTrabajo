"""Safe upgrade of the explicitly registered demonstration offer fixtures."""

import copy
import json
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from categorias.models import Categoria
from ia.models import EstadoPerfil, EventoSalida, PerfilOferta, TrabajoExtraccion, VersionPerfilOferta
from ia.workflow import offer_snapshot, publish_offer_profile
from ien_contracts.models import JobOffer
from ien_contracts.utils import content_hash
from matching.models import ResultadoCompatibilidad
from usuarios.models import Usuario

from .management.commands.actualizar_ofertas_demo_v2 import DEMO_OFFERS, PROMPT_VERSION, golden_fields
from .models import Oferta


class DemoOfferUpgradeTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        settings_patch = override_settings(BASE_DIR=Path(self.temp.name))
        settings_patch.enable()
        self.addCleanup(settings_patch.disable)
        self.companies = {
            email: Usuario.objects.create_user(email=email)
            for email in {spec.company_email for spec in DEMO_OFFERS}
        }

    def legacy_offer(self, spec=DEMO_OFFERS[0]):
        category, _ = Categoria.objects.get_or_create(nombre=spec.category)
        offer = Oferta.objects.create(
            empresa=self.companies[spec.company_email], categoria=category,
            estado='activa', fecha_cierre=timezone.now() + timedelta(days=20), **golden_fields(spec),
        )
        original = JobOffer.model_validate({
            'offer_id': str(offer.pk), 'title': spec.title, 'location': 'Córdoba',
            'work_mode': {'remoto': 'remote', 'hibrido': 'hybrid', 'presencial': 'onsite'}[spec.mode],
            'requirements': [{'name': name, 'minimum_level': 'intermediate', 'mandatory': True} for name in spec.skills],
        }).model_dump(mode='json')
        profile = PerfilOferta.objects.create(
            oferta=offer, contenido=original, schema_version='job-offer.v1', estado=EstadoPerfil.LISTO,
            version=1, source_hash=content_hash(original),
        )
        VersionPerfilOferta.objects.create(perfil=profile, version=1, contenido=original, content_hash=profile.source_hash)
        return offer

    def command(self, apply=False):
        output = StringIO()
        arguments = ['--apply'] if apply else []
        call_command('actualizar_ofertas_demo_v2', *arguments, stdout=output)
        return json.loads(output.getvalue())

    def test_default_dry_run_does_not_change_database_or_create_backups(self):
        offer = self.legacy_offer()
        original = copy.deepcopy(offer.perfil_ia.contenido)
        report = self.command()
        self.assertEqual(report['mode'], 'dry_run')
        self.assertEqual(report['counts']['eligible'], 1)
        self.assertIsNone(report['backup'])
        offer.refresh_from_db()
        self.assertTrue(offer.requiere_revision_requisitos)
        self.assertEqual(offer.perfil_ia.contenido, original)
        self.assertFalse(TrabajoExtraccion.objects.exists())
        self.assertFalse((Path(self.temp.name) / 'private_backups').exists())

    def test_apply_upgrades_nine_golden_demos_without_ia_outbox_or_fake_matches(self):
        offers = [self.legacy_offer(spec) for spec in DEMO_OFFERS]
        original_descriptions = {offer.pk: offer.descripcion for offer in offers}
        with patch('ia.workflow.request_offer_extraction') as dispatch:
            report = self.command(apply=True)
        dispatch.assert_not_called()
        self.assertEqual(report['counts']['applied'], 9)
        self.assertFalse(EventoSalida.objects.exists())
        self.assertFalse(ResultadoCompatibilidad.objects.exists())
        self.assertEqual(TrabajoExtraccion.objects.count(), 9)
        backup = json.loads(Path(report['backup']).read_text(encoding='utf-8'))
        self.assertEqual(len(backup['offers']), 9)
        self.assertTrue(all(item['fields']['requiere_revision_requisitos'] for item in backup['offers']))
        self.assertTrue(all(item['fields']['schema_version'] == 'job-offer.v1' for item in backup['profiles']))
        self.assertEqual(backup['extraction_jobs'], [])
        for offer, spec in zip(offers, DEMO_OFFERS):
            offer.refresh_from_db()
            self.assertEqual(offer.estado, 'activa')
            self.assertEqual(offer.descripcion, original_descriptions[offer.pk])
            self.assertFalse(offer.requiere_revision_requisitos)
            self.assertEqual(offer.experiencia_clasificacion, 'deseable')
            self.assertEqual(offer.educacion_clasificacion, 'deseable')
            profile = PerfilOferta.objects.get(oferta=offer)
            self.assertEqual(profile.schema_version, 'job-offer.v2')
            self.assertEqual(profile.estado, EstadoPerfil.LISTO)
            self.assertEqual(profile.version, 2)
            self.assertEqual(profile.versiones.get(version=1).contenido['schema_version'], 'job-offer.v1')
            self.assertEqual([row['name'] for row in profile.contenido['requirements'] if row['mandatory']], list(spec.skills))
            for requirement in profile.contenido['requirements']:
                if requirement['mandatory']:
                    self.assertEqual(requirement['category'], 'soft_skills' if requirement['name'] in {'Communication', 'Organization'} else 'technical_skills')
                else:
                    self.assertEqual(requirement['category'], 'desirables')
            job = TrabajoExtraccion.objects.get(oferta=offer)
            self.assertEqual(job.estado, TrabajoExtraccion.Estado.COMPLETADO)
            self.assertEqual(job.prompt_version, PROMPT_VERSION)
            self.assertEqual(job.profile_snapshot, offer_snapshot(offer))
            self.assertEqual(job.source_hash, content_hash(offer_snapshot(offer)))
            self.assertEqual(job.remote_job_id, '')
        second = self.command(apply=True)
        self.assertEqual(second['counts']['already_updated'], 9)
        self.assertIsNone(second['backup'])
        self.assertEqual(TrabajoExtraccion.objects.count(), 9)
        self.assertEqual(VersionPerfilOferta.objects.count(), 18)
        self.assertEqual(len(list((Path(self.temp.name) / 'private_backups').glob('*.json'))), 1)

    def test_modified_demo_is_reported_for_manual_review_and_not_changed(self):
        offer = self.legacy_offer()
        offer.descripcion = 'Changed by the owner; preserve this content.'
        offer.save(update_fields=['descripcion'])
        report = self.command(apply=True)
        self.assertEqual(report['counts']['needs_manual_review'], 1)
        item = next(row for row in report['offers'] if row.get('offer_id') == offer.pk)
        self.assertEqual(item['mismatched_fields'], ['descripcion'])
        offer.refresh_from_db()
        self.assertTrue(offer.requiere_revision_requisitos)
        self.assertEqual(offer.descripcion, 'Changed by the owner; preserve this content.')
        self.assertEqual(offer.perfil_ia.schema_version, 'job-offer.v1')
        self.assertFalse(TrabajoExtraccion.objects.exists())
        self.assertIsNone(report['backup'])

    def test_real_offer_and_changed_legacy_profile_are_never_overwritten(self):
        offer = self.legacy_offer()
        profile = offer.perfil_ia
        profile.contenido['requirements'][0]['mandatory'] = False
        profile.save(update_fields=['contenido'])
        real_owner = Usuario.objects.create_user(email='real-company@example.com')
        real = Oferta.objects.create(
            empresa=real_owner, categoria=offer.categoria, estado='activa',
            fecha_cierre=timezone.now() + timedelta(days=5), **golden_fields(DEMO_OFFERS[0]),
        )
        report = self.command(apply=True)
        self.assertEqual(report['counts']['needs_manual_review'], 1)
        self.assertNotIn(real.pk, [row.get('offer_id') for row in report['offers']])
        real.refresh_from_db()
        self.assertTrue(real.requiere_revision_requisitos)
        self.assertFalse(TrabajoExtraccion.objects.exists())
        profile.refresh_from_db()
        self.assertFalse(profile.contenido['requirements'][0]['mandatory'])

    def test_non_active_and_duplicate_golden_records_are_not_applied(self):
        first = self.legacy_offer()
        self.legacy_offer()
        inactive = self.legacy_offer(DEMO_OFFERS[1])
        inactive.estado = 'pendiente'
        inactive.save(update_fields=['estado'])
        report = self.command(apply=True)
        self.assertEqual(report['counts']['needs_manual_review'], 2)
        self.assertEqual(report['counts']['skipped_not_active'], 1)
        self.assertFalse(TrabajoExtraccion.objects.exists())
        first.refresh_from_db()
        self.assertTrue(first.requiere_revision_requisitos)

    def test_database_changes_roll_back_together_if_publication_fails(self):
        offers = [self.legacy_offer(spec) for spec in DEMO_OFFERS[:2]]
        calls = 0

        def fail_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError('synthetic publication failure')
            return publish_offer_profile(*args, **kwargs)

        with patch('ofertas.management.commands.actualizar_ofertas_demo_v2.publish_offer_profile', side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, 'synthetic publication failure'):
                self.command(apply=True)
        for offer in offers:
            offer.refresh_from_db()
            self.assertTrue(offer.requiere_revision_requisitos)
            self.assertEqual(offer.perfil_ia.schema_version, 'job-offer.v1')
        self.assertFalse(TrabajoExtraccion.objects.exists())
        self.assertEqual(VersionPerfilOferta.objects.count(), 2)
        self.assertEqual(len(list((Path(self.temp.name) / 'private_backups').glob('*.json'))), 1)
