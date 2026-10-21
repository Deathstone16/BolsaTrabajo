"""Validación estricta y normalización de archivos subidos."""

from __future__ import annotations

import io
import warnings
import zipfile
import subprocess
import tempfile
import shutil
import sys
from pathlib import Path
from pathlib import PurePosixPath

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from PIL import Image, ImageOps, UnidentifiedImageError

CV_MAX_BYTES = 5 * 1024 * 1024
IMAGE_MAX_PIXELS = 16_000_000
IMAGE_MAX_SIDE = 4096
CV_BASE_FORMATS = ('pdf', 'docx', 'odt', 'txt')


def cv_enabled_formats():
    return (*CV_BASE_FORMATS, 'doc', 'rtf') if (
        getattr(settings, 'CV_LEGACY_CONVERTER_IMAGE', '')
        and shutil.which(getattr(settings, 'CV_DOCKER_COMMAND', 'docker'))
    ) else CV_BASE_FORMATS


def _read_limited(upload, limit=CV_MAX_BYTES):
    if upload.size > limit:
        raise ValidationError('El archivo supera el tamaño máximo permitido de 5 MiB.')
    upload.seek(0)
    data = upload.read(limit + 1)
    upload.seek(0)
    if len(data) > limit:
        raise ValidationError('El archivo supera el tamaño máximo permitido de 5 MiB.')
    return data


def _validate_office_zip(data, extension):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 200:
                raise ValidationError('El documento contiene demasiados componentes.')
            total = 0
            for entry in entries:
                path = PurePosixPath(entry.filename)
                if path.is_absolute() or '..' in path.parts or entry.flag_bits & 1:
                    raise ValidationError('El documento comprimido no es seguro o está protegido.')
                total += entry.file_size
                if total > 50 * 1024 * 1024 or (entry.compress_size == 0 and entry.file_size > 0):
                    raise ValidationError('El documento comprimido supera los límites de seguridad.')
                if entry.compress_size and entry.file_size / entry.compress_size > 100:
                    raise ValidationError('El documento comprimido supera los límites de seguridad.')
            names = {entry.filename for entry in entries}
            if extension == 'docx':
                if '[Content_Types].xml' not in names or 'word/document.xml' not in names:
                    raise ValidationError('El archivo no tiene una estructura DOCX válida.')
                if any('vbaproject' in name.lower() or name.lower().endswith('.bin') for name in names):
                    raise ValidationError('No se admiten documentos Word con macros o contenido activo.')
                _validate_primary_office_xml(data, 'docx')
            rels = [name for name in names if name.lower().endswith('.rels')]
            for name in rels:
                with archive.open(name) as source:
                    raw = source.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise ValidationError('El documento contiene referencias XML demasiado grandes.')
                if b'<!doctype' in raw.lower() or b'<!entity' in raw.lower():
                    raise ValidationError('El documento contiene XML no permitido.')
                try:
                    from defusedxml import ElementTree
                    xml = ElementTree.fromstring(raw)
                except Exception:
                    raise ValidationError('El documento está dañado o tiene una estructura inválida.')
                for node in xml.iter():
                    if node.attrib.get('TargetMode', '').casefold() == 'external':
                        # Hipervínculos son texto inerte: Word no los resuelve al abrir ni al analizar.
                        if not node.attrib.get('Type', '').casefold().endswith('/hyperlink'):
                            raise ValidationError('El documento contiene plantillas o referencias externas activas.')
            if extension == 'odt':
                if 'mimetype' not in names or archive.read('mimetype') != b'application/vnd.oasis.opendocument.text' or 'content.xml' not in names:
                    raise ValidationError('El archivo no tiene una estructura ODT válida.')
                _validate_primary_office_xml(data, 'odt')
                if any(name.casefold().startswith(('scripts/', 'basic/')) for name in names):
                    raise ValidationError('El documento contiene scripts no permitidos.')
                with archive.open('content.xml') as source:
                    raw = source.read(5 * 1024 * 1024 + 1)
                if len(raw) > 5 * 1024 * 1024:
                    raise ValidationError('El contenido XML del documento supera el límite permitido.')
                if b'<!doctype' in raw.lower() or b'<!entity' in raw.lower():
                    raise ValidationError('El documento contiene XML no permitido.')
                try:
                    from defusedxml import ElementTree
                    content_xml = ElementTree.fromstring(raw)
                except Exception:
                    raise ValidationError('El documento está dañado o tiene una estructura inválida.')
                for node in content_xml.iter():
                    href = next((value for key, value in node.attrib.items() if key.endswith('}href')), '')
                    if href and not node.tag.endswith('}a'):
                        raise ValidationError('El documento contiene objetos o recursos externos activos.')
    except (zipfile.BadZipFile, OSError, KeyError):
        raise ValidationError('El documento está dañado o tiene una estructura inválida.')


def validate_cv_upload(upload) -> tuple[str, str, int]:
    """Valida extensión y estructura antes de conservar el archivo."""
    extension = upload.name.rsplit('.', 1)[-1].lower() if '.' in upload.name else ''
    if extension not in cv_enabled_formats():
        enabled = ', '.join(item.upper() for item in cv_enabled_formats())
        raise ValidationError(f'Formato no disponible. Se aceptan {enabled}.')
    data = _read_limited(upload)
    if not data:
        raise ValidationError('El archivo está vacío.')
    if extension == 'pdf':
        if not data.startswith(b'%PDF-') or b'%%EOF' not in data[-2048:]:
            raise ValidationError('El archivo no contiene un PDF válido.')
    elif extension in {'docx', 'odt'}:
        _validate_office_zip(data, extension)
    elif extension == 'doc':
        if not data.startswith(bytes.fromhex('D0CF11E0A1B11AE1')):
            raise ValidationError('El contenido no corresponde a un documento DOC.')
        _validate_legacy_conversion(data, extension)
    elif extension == 'rtf':
        if not data.startswith(b'{\\rtf'):
            raise ValidationError('El contenido no corresponde a un documento RTF.')
        _validate_legacy_conversion(data, extension)
    else:
        if data.startswith((b'%PDF-', bytes.fromhex('504B0304'), bytes.fromhex('D0CF11E0A1B11AE1'), b'{\\rtf')):
            raise ValidationError('La extensión del archivo no coincide con su contenido.')
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = data.decode('cp1252')
            except UnicodeDecodeError:
                raise ValidationError('El archivo de texto debe estar codificado en UTF-8 o Windows-1252.')
        if '\x00' in text or not text.strip() or sum(ord(ch) < 32 and ch not in '\r\n\t\f' for ch in text) > max(2, len(text) // 100):
            raise ValidationError('El contenido TXT está vacío o no parece ser texto.')
        if len(text) > 100_000:
            raise ValidationError('El texto supera el máximo permitido de 100.000 caracteres.')
    if extension == 'pdf':
        # Parseo en proceso separado con timeout: nunca descomprime streams de un PDF dentro
        # del proceso que atiende la solicitud web.
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as handle:
            path = Path(handle.name)
            handle.write(data)
        try:
            try:
                completed = subprocess.run(
                    [sys.executable, '-c', _PDF_VALIDATION_SCRIPT, str(path)],
                    capture_output=True, timeout=10, check=False, shell=False,
                )
            except (OSError, subprocess.SubprocessError):
                raise ValidationError('No se pudo validar el PDF de forma segura; el CV no se guardó.')
            if completed.returncode == 2:
                raise ValidationError('El PDF debe tener entre 1 y 20 páginas.')
            if completed.returncode == 3:
                raise ValidationError('El PDF no contiene texto seleccionable. Si es escaneado, cargá una versión con texto.')
            if completed.returncode != 0:
                raise ValidationError('El archivo no es un PDF válido o no se pudo leer.')
        finally:
            path.unlink(missing_ok=True)
    mime = {
        'pdf': 'application/pdf', 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'odt': 'application/vnd.oasis.opendocument.text', 'txt': 'text/plain',
        'doc': 'application/msword', 'rtf': 'application/rtf',
    }[extension]
    return extension, mime, len(data)


def _validate_legacy_conversion(data, extension):
    image = getattr(settings, 'CV_LEGACY_CONVERTER_IMAGE', '')
    docker = shutil.which(getattr(settings, 'CV_DOCKER_COMMAND', 'docker'))
    if not image or not docker:
        raise ValidationError(f'El formato {extension.upper()} requiere un conversor aislado configurado.')
    try:
        with tempfile.TemporaryDirectory(prefix='ien-cv-convert-') as temporary:
            root = Path(temporary)
            input_dir, output_dir = root / 'input', root / 'output'
            input_dir.mkdir(); output_dir.mkdir()
            (input_dir / f'document.{extension}').write_bytes(data)
            from uuid import uuid4
            container_name = f'ien-cv-convert-{uuid4().hex}'
            command = [
                docker, 'run', '--rm', '--name', container_name, '--network', 'none', '--memory', '512m', '--cpus', '1',
                '--pids-limit', '64', '--read-only', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges', '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m',
                '-v', f'{input_dir.resolve()}:/input:ro', '-v', f'{output_dir.resolve()}:/output:rw',
                image, '--headless', '-env:UserInstallation=file:///tmp/lo-profile', '--convert-to',
                'txt:Text', '--outdir', '/output', f'/input/document.{extension}',
            ]
            try:
                result = subprocess.run(
                    command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=getattr(settings, 'CV_LEGACY_CONVERSION_TIMEOUT_SECONDS', 35),
                    check=False, shell=False,
                )
            finally:
                try:
                    subprocess.run(
                        [docker, 'rm', '--force', container_name], stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
                        check=False, shell=False,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    pass
            output = output_dir / 'document.txt'
            if result.returncode or not output.is_file() or output.stat().st_size > 400_000:
                raise ValidationError('No se pudo convertir el documento de forma segura; guardalo como DOCX o PDF.')
            text = output.read_text(encoding='utf-8', errors='strict')
            if not text.strip() or len(text) > 100_000:
                raise ValidationError('El documento convertido está vacío o supera el límite de texto permitido.')
    except ValidationError:
        raise
    except subprocess.TimeoutExpired:
        raise ValidationError('La conversión superó el tiempo máximo; el archivo no se guardó.')
    except (OSError, UnicodeError, subprocess.SubprocessError):
        raise ValidationError('El conversor aislado no está disponible o no pudo validar el archivo.')


def _validate_primary_office_xml(data, document_format):
    """Parsea el XML principal fuera del proceso web, con memoria acotada."""
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as handle:
        path = Path(handle.name)
        handle.write(data)
    script = r'''import sys, zipfile
from ien_contracts.process_limits import configure_process_limits
configure_process_limits(512 * 1024 * 1024)
from defusedxml import ElementTree
try:
    with zipfile.ZipFile(sys.argv[1]) as archive:
        fmt = sys.argv[2]
        names = archive.namelist()
        import re
        targets = (sorted(name for name in names if name == 'word/document.xml' or
                    re.fullmatch(r'word/(header|footer)\d+\.xml', name)) if fmt == 'docx' else ['content.xml'])
        parts = []
        for name in targets:
            info = archive.getinfo(name)
            if info.file_size > 10 * 1024 * 1024:
                raise SystemExit(3)
            with archive.open(info) as source:
                raw = source.read(10 * 1024 * 1024 + 1)
            if len(raw) > 10 * 1024 * 1024:
                raise SystemExit(3)
            root = ElementTree.fromstring(raw)
            if fmt == 'docx':
                for node in root.iter():
                    if node.tag.endswith('}t') and node.text:
                        parts.append(node.text)
                    elif node.tag.endswith('}p'):
                        parts.append('\n')
                    elif node.tag.endswith('}tab'):
                        parts.append('\t')
            else:
                def walk(node):
                    if node.text:
                        parts.append(node.text)
                    for child in list(node):
                        walk(child)
                        if child.tail:
                            parts.append(child.tail)
                        if child.tag.endswith('}p') or child.tag.endswith('}h'):
                            parts.append('\n')
                walk(root)
        text = ''.join(parts).strip()
        if len(text) > 100000:
            raise SystemExit(3)
        if not text.strip():
            raise SystemExit(2)
except SystemExit:
    raise
except Exception:
    raise SystemExit(1)
'''
    try:
        try:
            completed = subprocess.run(
                [sys.executable, '-c', script, str(path), document_format],
                capture_output=True, timeout=20, check=False, shell=False,
            )
        except (OSError, subprocess.SubprocessError):
            raise ValidationError('No se pudo validar el documento de forma segura; el CV no se guardó.')
        if completed.returncode == 2:
            raise ValidationError('El documento está vacío o no contiene texto legible.')
        if completed.returncode == 3:
            raise ValidationError('El texto extraído supera el límite de 100.000 caracteres permitido.')
        if completed.returncode != 0:
            raise ValidationError('El documento está dañado o tiene una estructura XML inválida.')
    finally:
        path.unlink(missing_ok=True)


_PDF_VALIDATION_SCRIPT = r'''import sys
from ien_contracts.process_limits import configure_process_limits
configure_process_limits(512 * 1024 * 1024)
from pypdf import PdfReader
try:
    reader = PdfReader(sys.argv[1], strict=True)
    if not 1 <= len(reader.pages) <= 20:
        raise SystemExit(2)
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or '')
        if sum(map(len, parts)) > 100000:
            raise SystemExit(4)
    if not ''.join(parts).strip():
        raise SystemExit(3)
except SystemExit:
    raise
except Exception:
    raise SystemExit(1)
'''


def scan_cv_upload(upload):
    """Escanea antes de guardar; cualquier error del motor bloquea el reemplazo."""
    if not getattr(settings, 'CV_SCAN_ENABLED', False):
        return
    command = getattr(settings, 'CV_SCAN_COMMAND', '')
    timeout = getattr(settings, 'CV_SCAN_TIMEOUT_SECONDS', 30)
    if not command:
        raise ValidationError('El escáner de archivos no está configurado; el CV no se guardó.')
    root = Path(settings.BASE_DIR) / 'private_uploads' / 'quarantine'
    root.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.name).suffix.lower()
    try:
        with tempfile.NamedTemporaryFile(prefix='cv-', suffix=suffix, dir=root, delete=False) as handle:
            temp_path = Path(handle.name)
            upload.seek(0)
            for chunk in upload.chunks():
                handle.write(chunk)
        completed = subprocess.run(
            [command, '-Scan', '-ScanType', '3', '-File', str(temp_path), '-DisableRemediation'],
            capture_output=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
        if completed.returncode != 0:
            raise ValidationError('El escáner no pudo confirmar que el CV sea seguro; no se guardó.')
    except (OSError, subprocess.SubprocessError):
        raise ValidationError('El escáner de archivos no está disponible; no se guardó el CV.')
    finally:
        if 'temp_path' in locals():
            temp_path.unlink(missing_ok=True)
        upload.seek(0)


def normalize_image_upload(upload, *, max_bytes, max_side=IMAGE_MAX_SIDE):
    if upload.size > max_bytes:
        raise ValidationError('La imagen supera el tamaño máximo permitido.')
    upload.seek(0)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            upload.seek(0)
            with Image.open(upload) as image:
                if image.format not in {'JPEG', 'PNG', 'WEBP'} or getattr(image, 'n_frames', 1) != 1:
                    raise ValidationError('Usá una imagen JPG, PNG o WebP estática.')
                width, height = image.size
                if width > IMAGE_MAX_SIDE or height > IMAGE_MAX_SIDE or width * height > IMAGE_MAX_PIXELS:
                    raise ValidationError('La imagen supera los límites de dimensiones permitidos.')
                image.verify()
            upload.seek(0)
            with Image.open(upload) as image:
                image = ImageOps.exif_transpose(image).convert('RGB')
                image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                output = io.BytesIO()
                image.save(output, format='WEBP', quality=88, method=6)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError('La imagen está dañada o no se puede procesar de forma segura.')
    from uuid import uuid4
    return ContentFile(output.getvalue(), name=uuid4().hex + '.webp')
