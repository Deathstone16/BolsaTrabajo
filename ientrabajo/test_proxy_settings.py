"""Host y CSRF detrás de un proxy HTTPS, sin base de datos ni proveedor IA."""

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


PROBE = '''
import json
import django
django.setup()
from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from django.test import RequestFactory
from django.http import HttpResponse
factory = RequestFactory()
middleware = CsrfViewMiddleware(lambda request: HttpResponse())
results = []
for origin in ('https://bolsa.example.com', 'https://otro.example.com'):
    request = factory.post('/', HTTP_HOST='bolsa.example.com', HTTP_ORIGIN=origin,
        HTTP_X_FORWARDED_PROTO='https', HTTP_X_CSRFTOKEN='a' * 32,
        HTTP_COOKIE='csrftoken=' + 'a' * 32)
    middleware.process_request(request)
    response = middleware.process_view(request, lambda request: HttpResponse(), (), {})
    results.append({'secure': request.is_secure(), 'status': response.status_code if response else 200})
print(json.dumps({'results': results, 'origins': settings.CSRF_TRUSTED_ORIGINS}))
'''


class ProxySettingsTests(unittest.TestCase):
    def probe(self, trust_proxy):
        env = os.environ.copy()
        env.update({
            'DJANGO_SETTINGS_MODULE': 'ientrabajo.settings.base',
            'DEBUG': 'true', 'DB_ENGINE': 'sqlite',
            'SECRET_KEY': 'test-only-proxy-settings',
            'ALLOWED_HOSTS': 'bolsa.example.com,localhost',
            'CSRF_TRUSTED_ORIGINS': ' https://bolsa.example.com , ',
            'TRUST_PROXY_HEADERS': str(trust_proxy).lower(),
        })
        result = subprocess.run([sys.executable, '-c', PROBE],
            cwd=Path(__file__).resolve().parent.parent, env=env,
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_https_proxy_accepts_trusted_origin_and_rejects_foreign_origin(self):
        result = self.probe(True)
        self.assertEqual(result['origins'], ['https://bolsa.example.com'])
        self.assertEqual(result['results'], [
            {'secure': True, 'status': 200},
            {'secure': True, 'status': 403},
        ])

    def test_untrusted_proxy_header_does_not_mark_request_as_secure(self):
        result = self.probe(False)
        self.assertFalse(any(row['secure'] for row in result['results']))
        self.assertEqual(result['results'][1]['status'], 403)
