"""Migra CV anteriores del directorio público al almacén privado."""

from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.core.files.utils import validate_file_name
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.db import transaction
from django.utils._os import safe_join

from ia.models import CVVersion, TrabajoExtraccion, private_cv_storage
from usuarios.models import Postulante
from usuarios.uploads import validate_cv_upload


class Command(BaseCommand):
    help = 'Copia CV heredados a almacenamiento privado. Sin --apply solo informa.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Copia los archivos, actualiza los perfiles y retira el original público.')
        parser.add_argument('--limit', type=int, default=0)

    def handle(self, *args, **options):
        rows = Postulante.objects.exclude(cv='').order_by('pk')
        snapshots = TrabajoExtraccion.objects.filter(cv_snapshot__startswith='ia/extraction_snapshots/').order_by('pk')
        limit = options['limit']
        if limit:
            # El límite es global para que una corrida acotada no procese el doble.
            cv_count = rows.count()
            rows = rows[:limit]
            snapshots = snapshots[:max(0, limit - min(cv_count, limit))]
        if not options['apply']:
            self.stdout.write(
                f'Modo de revisión: {rows.count()} CV heredados y {snapshots.count()} snapshots '
                'requieren copia privada. Usá --apply después de validar el respaldo.'
            )
            return
        migrated_cv = migrated_snapshots = 0
        for item in rows.iterator():
            try:
                self._migrate_one(item.pk)
                migrated_cv += 1
            except (OSError, ValueError, ValidationError, CommandError) as exc:
                self.stderr.write(self.style.ERROR(f'Postulante {item.pk}: no se pudo migrar el CV; el original se conserva. {exc}'))
        for job in snapshots.iterator():
            try:
                migrated_snapshots += bool(self._migrate_snapshot(job.pk))
            except (OSError, ValueError, ValidationError, CommandError) as exc:
                self.stderr.write(self.style.ERROR(f'TrabajoExtraccion {job.pk}: no se pudo migrar el snapshot; el original se conserva. {exc}'))
        self.stdout.write(self.style.SUCCESS(f'CV migrados: {migrated_cv}; snapshots migrados: {migrated_snapshots}'))

    @staticmethod
    def _legacy_source_path(name):
        """Comprueba que una referencia heredada apunte dentro de MEDIA_ROOT."""
        name = validate_file_name(name, allow_relative_path=True)
        try:
            source_path = Path(default_storage.path(name)).resolve()
            media_root = Path(settings.MEDIA_ROOT).resolve()
            safe_join(str(media_root), name)
        except (NotImplementedError, ValueError, SuspiciousFileOperation) as exc:
            raise CommandError('El almacenamiento heredado no permite una comprobación local de ruta.') from exc
        if media_root not in source_path.parents:
            raise CommandError('La ruta heredada queda fuera de MEDIA_ROOT.')
        if not source_path.is_file():
            raise CommandError('El archivo heredado no existe o no es un archivo regular.')
        return name

    @transaction.atomic
    def _migrate_one(self, postulante_id):
        postulante = Postulante.objects.select_for_update().get(pk=postulante_id)
        if not postulante.cv:
            return
        old_name = self._legacy_source_path(postulante.cv.name)
        source_marker = ('legacy:' + old_name)[:255]
        existing = CVVersion.objects.filter(postulante=postulante, nombre_original=source_marker).first()
        if existing is None:
            digest = sha256()
            with default_storage.open(old_name, 'rb') as source:
                for block in iter(lambda: source.read(128 * 1024), b''):
                    digest.update(block)
            size = default_storage.size(old_name)
            extension = Path(old_name).suffix.lower().lstrip('.')
            valid_format = extension
            try:
                with default_storage.open(old_name, 'rb') as source:
                    source.name = Path(old_name).name
                    validate_cv_upload(source)
            except (ValidationError, OSError, ValueError):
                valid_format = 'legacy'
            number = (postulante.versiones_cv.order_by('-numero').values_list('numero', flat=True).first() or 0) + 1
            version = CVVersion(
                postulante=postulante,
                numero=number,
                nombre_original=source_marker,
                sha256=digest.hexdigest(),
                formato=valid_format[:12],
                tamano=size,
            )
            with default_storage.open(old_name, 'rb') as source:
                version.archivo.save(f'{uuid4().hex}.{valid_format}', File(source), save=False)
            version.save()
        else:
            version = existing
        if version.formato != 'legacy' and not postulante.cv_version_actual_id:
            postulante.cv_version_actual = version
            postulante.cv_fecha_carga = postulante.cv_fecha_carga or version.creado_en
        postulante.cv = None
        postulante.save(update_fields=['cv', 'cv_version_actual', 'cv_fecha_carga'])
        transaction.on_commit(lambda: default_storage.delete(old_name))

    @transaction.atomic
    def _migrate_snapshot(self, job_id):
        job = TrabajoExtraccion.objects.select_for_update().get(pk=job_id)
        if not job.cv_snapshot:
            return False
        if job.cv_snapshot.name.replace('\\', '/').casefold().startswith('snapshots/'):
            return False
        old_name = self._legacy_source_path(job.cv_snapshot.name)
        # Only the known legacy snapshot tree is eligible for this one-time move.
        normalized = old_name.replace('\\', '/').casefold()
        if not normalized.startswith('ia/extraction_snapshots/'):
            raise CommandError('El snapshot heredado no está dentro de ia/extraction_snapshots/.')

        digest = sha256()
        with default_storage.open(old_name, 'rb') as source:
            for block in iter(lambda: source.read(128 * 1024), b''):
                digest.update(block)
        suffix = Path(old_name).suffix.lower()[:12]
        target_name = f'snapshots/legacy-{job.pk}-{digest.hexdigest()}{suffix}'
        if private_cv_storage.exists(target_name):
            # A previous interrupted attempt may have completed the copy but not
            # changed the database reference. Verify bytes before reusing it.
            target_hash = sha256()
            with private_cv_storage.open(target_name, 'rb') as target:
                for block in iter(lambda: target.read(128 * 1024), b''):
                    target_hash.update(block)
            if target_hash.hexdigest() != digest.hexdigest():
                raise CommandError('El snapshot privado existente no coincide con el original.')
            new_name = target_name
            copied_now = False
        else:
            try:
                with default_storage.open(old_name, 'rb') as source:
                    new_name = private_cv_storage.save(target_name, File(source))
                copied_now = True
                # FieldFile.save chooses its own collision-safe name. Do not
                # silently accept a different target with mismatched contents.
                copied_hash = sha256()
                with private_cv_storage.open(new_name, 'rb') as copied:
                    for block in iter(lambda: copied.read(128 * 1024), b''):
                        copied_hash.update(block)
                if copied_hash.hexdigest() != digest.hexdigest():
                    raise CommandError('La copia privada del snapshot no coincide con el original.')
            except Exception:
                if 'new_name' in locals() and copied_now:
                    private_cv_storage.delete(new_name)
                raise

        job.cv_snapshot.name = new_name
        try:
            job.save(update_fields=['cv_snapshot', 'actualizado_en'])
        except Exception:
            if copied_now:
                private_cv_storage.delete(new_name)
            raise
        transaction.on_commit(lambda: default_storage.delete(old_name))
        return True
