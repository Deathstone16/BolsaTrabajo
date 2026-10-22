"""Upgrade only unchanged, explicitly registered legacy DEMO offer fixtures."""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from ia.models import EstadoPerfil, PerfilOferta, TrabajoExtraccion, VersionPerfilOferta
from ia.workflow import offer_snapshot, publish_offer_profile
from ien_contracts.models import JobOffer
from ien_contracts.utils import content_hash
from ofertas.models import Oferta


PROMPT_VERSION = 'demo-offer.v2'
COMPANY = 'empresa@demo.example.test'
AGENCY = 'agencia@demo.example.test'


@dataclass(frozen=True)
class DemoOffer:
    title: str
    category: str
    skills: tuple[str, ...]
    mode: str
    company_email: str


# Explicit golden records from seed_demo; never infer policy for real offers.
DEMO_OFFERS = (
    DemoOffer('Desarrollador Python / Django', 'Tecnología', ('Python', 'Django', 'SQL'), 'remoto', COMPANY),
    DemoOffer('Frontend React junior', 'Tecnología', ('JavaScript', 'React', 'CSS'), 'hibrido', COMPANY),
    DemoOffer('Soporte técnico junior', 'Tecnología', ('Customer service', 'Windows', 'Networking'), 'presencial', COMPANY),
    DemoOffer('Analista de datos', 'Tecnología', ('Python', 'SQL', 'Excel'), 'remoto', COMPANY),
    DemoOffer('Community manager', 'Marketing y comunicación', ('Social media', 'Content creation', 'Canva'), 'hibrido', AGENCY),
    DemoOffer('Asistente de marketing', 'Marketing y comunicación', ('Communication', 'Canva', 'Excel'), 'remoto', AGENCY),
    DemoOffer('Auxiliar administrativo', 'Administración', ('Excel', 'Organization', 'Communication'), 'presencial', COMPANY),
    DemoOffer('Atención al cliente', 'Atención al cliente', ('Customer service', 'Communication'), 'hibrido', AGENCY),
    DemoOffer('Backend trainee sin experiencia', 'Tecnología', ('Python', 'Git'), 'remoto', COMPANY),
)


def golden_fields(spec: DemoOffer) -> dict:
    skills = ', '.join(spec.skills)
    return {
        'titulo': f'DEMO · {spec.title}', 'nombre_puesto': spec.title,
        'ubicacion': 'Córdoba, Argentina', 'modalidad': spec.mode,
        'experiencia_requerida': 'sin-experiencia' if any(word in spec.title.lower() for word in ('junior', 'trainee')) else '1-2',
        'nivel_educativo': 'secundario', 'habilidades_duras': skills,
        'habilidades_blandas': 'Comunicación, Trabajo en equipo', 'habilidades_requeridas': skills,
        'descripcion': (
            f'Oferta ficticia para pruebas: {spec.title}.\n'
            f'Buscamos una persona con conocimientos de {skills}.\n'
            'Acompañamiento del equipo, capacitación y oportunidades de crecimiento.\n'
            'Todos los datos de esta oferta son de demostración.'
        ),
        'motivo_rechazo': '', 'es_confidencial': False,
    }


def canonical_plan(offer: Oferta, spec: DemoOffer) -> tuple[dict, dict, str]:
    def requirement(name, category, source, mandatory, **extra):
        return {
            'id': str(uuid5(NAMESPACE_URL, f'ien:{PROMPT_VERSION}:{spec.company_email}:{spec.title}:{source}:{name.casefold()}')),
            'name': name, 'category': category, 'source': source,
            'mandatory': mandatory, 'exclusionary': False, **extra,
        }

    # Mandatory skills are exactly those explicitly mandatory in seed_demo's
    # original offer profile. Metadata tags do not introduce new obligations.
    requirements = [
        requirement(name, 'soft_skills' if name in {'Communication', 'Organization'} else 'technical_skills',
                    'requisitos_obligatorios', True, minimum_level='intermediate')
        for name in spec.skills
    ]
    # This is an explicit policy for these DEMO fixtures, never a legacy inference.
    requirements.extend([
        requirement(offer.get_experiencia_requerida_display(), 'desirables', 'experiencia_requerida', False,
                    minimum_years=0 if offer.experiencia_requerida == 'sin-experiencia' else 1),
        requirement(offer.get_nivel_educativo_display(), 'desirables', 'nivel_educativo', False),
    ])
    changes = {
        'requisitos_obligatorios': '\n'.join(spec.skills),
        'requisitos_deseables': (
            f'Experiencia: {offer.get_experiencia_requerida_display()}\n'
            f'Educación: {offer.get_nivel_educativo_display()}'
        ),
        'experiencia_clasificacion': 'deseable', 'educacion_clasificacion': 'deseable',
        'requisitos_estructurados': requirements, 'requiere_revision_requisitos': False,
    }
    planned = copy.copy(offer)
    for name, value in changes.items():
        setattr(planned, name, value)
    snapshot = offer_snapshot(planned)
    canonical = JobOffer.model_validate(snapshot).model_dump(mode='json')
    return changes, canonical, content_hash(snapshot)


def assess(offer: Oferta, spec: DemoOffer) -> tuple[str, list[str]]:
    if offer.estado != 'activa':
        return 'skipped_not_active', []
    changed = [name for name, value in golden_fields(spec).items() if getattr(offer, name) != value]
    if offer.categoria.nombre != spec.category:
        changed.append('categoria')
    if changed:
        return 'needs_manual_review', changed
    profile = PerfilOferta.objects.filter(oferta=offer).first()
    changes, canonical, source_hash = canonical_plan(offer, spec)
    if profile is not None and profile.schema_version == 'job-offer.v2':
        job_exists = TrabajoExtraccion.objects.filter(
            oferta=offer, tipo=TrabajoExtraccion.Tipo.OFERTA, prompt_version=PROMPT_VERSION,
            source_hash=source_hash, estado=TrabajoExtraccion.Estado.COMPLETADO,
        ).exists()
        if (all(getattr(offer, name) == value for name, value in changes.items())
                and profile.contenido == canonical and profile.estado == EstadoPerfil.LISTO and job_exists):
            return 'already_updated', []
        return 'needs_manual_review', ['perfil_v2_existente']
    if not offer.requiere_revision_requisitos:
        return 'needs_manual_review', ['requiere_revision_requisitos']
    legacy_defaults = {
        'requisitos_obligatorios': '', 'requisitos_deseables': '', 'requisitos_estructurados': [],
        'experiencia_clasificacion': 'no_solicitado', 'educacion_clasificacion': 'no_solicitado',
    }
    changed = [name for name, value in legacy_defaults.items() if getattr(offer, name) != value]
    if changed:
        return 'needs_manual_review', changed
    if profile is not None and profile.schema_version != 'job-offer.v1':
        return 'needs_manual_review', ['schema_version']
    if profile is not None:
        original = {
            'offer_id': str(offer.pk), 'title': spec.title, 'location': 'Córdoba',
            'work_mode': {'remoto': 'remote', 'hibrido': 'hybrid', 'presencial': 'onsite'}[spec.mode],
            'requirements': [{'name': name, 'minimum_level': 'intermediate', 'mandatory': True} for name in spec.skills],
        }
        try:
            original = JobOffer.model_validate(original).model_dump(mode='json')
            current = JobOffer.model_validate(profile.contenido).model_dump(mode='json')
        except ValueError:
            return 'needs_manual_review', ['perfil_contenido']
        if current != original:
            return 'needs_manual_review', ['perfil_contenido']
    return 'eligible', []


def write_backup(offers: list[Oferta]) -> Path:
    ids = [offer.pk for offer in offers]
    payload = {
        'schema_version': 'demo-offer-upgrade-backup.v1', 'created_at': timezone.now(),
        'offers': serializers.serialize('python', offers),
        'profiles': serializers.serialize('python', PerfilOferta.objects.filter(oferta_id__in=ids)),
        'profile_versions': serializers.serialize('python', VersionPerfilOferta.objects.filter(perfil__oferta_id__in=ids)),
        'extraction_jobs': serializers.serialize('python', TrabajoExtraccion.objects.filter(
            oferta_id__in=ids, tipo=TrabajoExtraccion.Tipo.OFERTA,
        )),
    }
    directory = Path(settings.BASE_DIR) / 'private_backups'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / f'demo-offer-v2-{timezone.now():%Y%m%d-%H%M%S}-{uuid4().hex}.json'
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as backup:
        json.dump(payload, backup, cls=DjangoJSONEncoder, ensure_ascii=False, indent=2)
        backup.write('\n')
    return path


class Command(BaseCommand):
    help = 'Prepara o aplica la actualización canónica v2 de las nueve ofertas DEMO originales sin IA.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Aplica el plan tras guardar un respaldo privado. Sin esta opción solo informa.')

    def handle(self, *args, **options):
        applying = options['apply']
        report = {'mode': 'apply' if applying else 'dry_run', 'fixture_version': PROMPT_VERSION, 'offers': [], 'backup': None}
        specs = {(spec.company_email, f'DEMO · {spec.title}'): spec for spec in DEMO_OFFERS}
        query = Q(pk__in=[])
        for email, title in specs:
            query |= Q(empresa__email=email, titulo=title)
        with transaction.atomic():
            queryset = Oferta.objects.filter(query).select_related('empresa', 'categoria').order_by('pk')
            if applying:
                queryset = queryset.select_for_update(of=('self',))
            candidates = list(queryset)
            eligible = []
            seen = set()
            for offer in candidates:
                key = (offer.empresa.email, offer.titulo)
                spec = specs[key]
                status, mismatches = assess(offer, spec)
                if key in seen:
                    status, mismatches = 'needs_manual_review', ['oferta_demo_duplicada']
                seen.add(key)
                item = {'offer_id': offer.pk, 'title': offer.titulo, 'status': status, 'mismatched_fields': mismatches}
                report['offers'].append(item)
                if status == 'eligible':
                    changes, canonical, source_hash = canonical_plan(offer, spec)
                    item['requirements'] = canonical['requirements']
                    eligible.append((offer, changes, canonical, source_hash, item))
            for key in specs:
                if key not in seen:
                    report['offers'].append({'title': key[1], 'status': 'missing', 'mismatched_fields': []})
            # Ambiguous duplicate titles are never applied, including their first occurrence.
            duplicated = {item['title'] for item in report['offers'] if 'oferta_demo_duplicada' in item['mismatched_fields']}
            eligible = [entry for entry in eligible if entry[0].titulo not in duplicated]
            for item in report['offers']:
                if item['title'] in duplicated:
                    item.update(status='needs_manual_review', mismatched_fields=['oferta_demo_duplicada'])
            if applying and eligible:
                report['backup'] = str(write_backup([entry[0] for entry in eligible]))
                for offer, changes, canonical, source_hash, item in eligible:
                    for name, value in changes.items():
                        setattr(offer, name, value)
                    offer.save(update_fields=list(changes))
                    publish_offer_profile(offer, canonical, source_hash)
                    job, created = TrabajoExtraccion.objects.get_or_create(
                        clave_idempotencia=f'{PROMPT_VERSION}:{offer.pk}:{source_hash}',
                        defaults={
                            'oferta': offer, 'tipo': TrabajoExtraccion.Tipo.OFERTA,
                            'prompt_version': PROMPT_VERSION, 'source_hash': source_hash,
                            'profile_snapshot': offer_snapshot(offer),
                            'estado': TrabajoExtraccion.Estado.COMPLETADO,
                        },
                    )
                    if not created and (job.oferta_id != offer.pk or job.tipo != TrabajoExtraccion.Tipo.OFERTA
                                        or job.estado != TrabajoExtraccion.Estado.COMPLETADO
                                        or job.prompt_version != PROMPT_VERSION or job.source_hash != source_hash
                                        or job.profile_snapshot != offer_snapshot(offer) or job.remote_job_id):
                        raise CommandError('El registro DEMO existente no coincide con el plan; se revirtió la transacción.')
                    item.update(status='applied', job_id=job.pk)
        report['counts'] = {status: sum(item['status'] == status for item in report['offers']) for status in sorted({item['status'] for item in report['offers']})}
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
