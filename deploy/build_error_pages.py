"""Run after error template changes: python deploy/build_error_pages.py."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ientrabajo.settings.base')
import django
django.setup()
from django.template.loader import render_to_string
from ientrabajo.error_pages import error_context

output = ROOT / 'static' / 'errors'
output.mkdir(exist_ok=True)
for code in (503, 504):
    (output / f'{code}.html').write_text(render_to_string('errors/page.html', error_context(code)), encoding='utf-8')
