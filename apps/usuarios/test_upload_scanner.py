"""El escáner de CV debe funcionar en Linux y fallar cerrado."""

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from .uploads import scan_cv_upload


class UploadScannerTests(SimpleTestCase):
    def test_clamav_scans_temporary_file_and_removes_it(self):
        with tempfile.TemporaryDirectory() as root:
            with override_settings(BASE_DIR=Path(root), CV_SCAN_ENABLED=True,
                                   CV_SCAN_BACKEND='clamav', CV_SCAN_COMMAND='/usr/bin/clamscan'):
                with patch('usuarios.uploads.subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
                    scan_cv_upload(SimpleUploadedFile('cv.pdf', b'archivo de prueba'))
                args = run.call_args.args[0]
                self.assertEqual(args[:2], ['/usr/bin/clamscan', '--no-summary'])
                self.assertFalse(Path(args[2]).exists())

    def test_clamav_rejects_infected_or_failed_scan(self):
        with tempfile.TemporaryDirectory() as root:
            with override_settings(BASE_DIR=Path(root), CV_SCAN_ENABLED=True,
                                   CV_SCAN_BACKEND='clamav', CV_SCAN_COMMAND='/usr/bin/clamscan'):
                for code in (1, 2):
                    with self.subTest(code=code):
                        with patch('usuarios.uploads.subprocess.run', return_value=SimpleNamespace(returncode=code)):
                            with self.assertRaises(ValidationError):
                                scan_cv_upload(SimpleUploadedFile('cv.pdf', b'archivo de prueba'))
