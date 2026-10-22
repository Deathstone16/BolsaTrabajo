import io
import signal
import subprocess
import sys
import unittest

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from .uploads import validate_cv_upload


class PDFParserProcessTests(SimpleTestCase):
    def test_valid_text_pdf_is_accepted_by_isolated_parser(self):
        writer = PdfWriter()
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject({
            NameObject('/Type'): NameObject('/Font'),
            NameObject('/Subtype'): NameObject('/Type1'),
            NameObject('/BaseFont'): NameObject('/Helvetica'),
        })
        page[NameObject('/Resources')] = DictionaryObject({
            NameObject('/Font'): DictionaryObject({NameObject('/F1'): font}),
        })
        stream = DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 20 200 Td (Synthetic CV Python Django) Tj ET')
        page[NameObject('/Contents')] = writer._add_object(stream)
        output = io.BytesIO()
        writer.write(output)
        upload = SimpleUploadedFile('synthetic.pdf', output.getvalue(), 'application/pdf')
        self.assertEqual(validate_cv_upload(upload)[0], 'pdf')

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS memory supervision')
    def test_monitor_terminates_parser_over_memory_budget(self):
        script = (
            'from ien_contracts.process_limits import configure_process_limits; '
            'configure_process_limits(1); '
            'import time; time.sleep(10)'
        )
        result = subprocess.run([sys.executable, '-c', script], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr.decode())
