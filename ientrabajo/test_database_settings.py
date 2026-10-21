"""Comprueba la elección de base sin tocar SQLite ni PostgreSQL."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INSPECT_SETTINGS = (
    'import json; '
    'from ientrabajo.settings.base import DATABASES; '
    'db = DATABASES["default"]; '
    'print(json.dumps({"engine": db["ENGINE"], '
    '"name": str(db["NAME"]), '
    '"sslmode": db.get("OPTIONS", {}).get("sslmode")}))'
)


class DatabaseSettingsTests(unittest.TestCase):
    def run_settings(self, **overrides):
        env = os.environ.copy()
        env.update({
            'DEBUG': 'true',
            'DB_ENGINE': 'sqlite',
            'DB_NAME': '',
            'DB_USER': '',
            'DB_PASSWORD': '',
            'DB_HOST': '',
            'DB_PORT': '',
            'DB_SSLMODE': '',
            'SECRET_KEY': 'test-key-only-for-settings-checks',
            'ALLOWED_HOSTS': 'localhost',
            'IA_CALLBACK_HMAC_SECRET': 'test-hmac-only',
        })
        env.update(overrides)
        return subprocess.run(
            [sys.executable, '-c', INSPECT_SETTINGS],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_sqlite_stays_available_in_development(self):
        result = self.run_settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['engine'], 'django.db.backends.sqlite3')

    def test_postgresql_can_be_selected_in_development(self):
        result = self.run_settings(
            DB_ENGINE='postgresql', DB_NAME='ien_dev', DB_USER='ien_dev',
            DB_PASSWORD='test-password', DB_HOST='127.0.0.1', DB_PORT='5433',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            'engine': 'django.db.backends.postgresql',
            'name': 'ien_dev',
            'sslmode': 'prefer',
        })

    def test_production_requires_postgresql(self):
        result = self.run_settings(DEBUG='false')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DB_ENGINE=postgresql', result.stderr)

    def test_production_requires_credentials_and_tls(self):
        missing = self.run_settings(DEBUG='false', DB_ENGINE='postgresql')
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('Faltan variables de PostgreSQL', missing.stderr)

        valid = self.run_settings(
            DEBUG='false', DB_ENGINE='postgresql', DB_NAME='ien',
            DB_USER='ien', DB_PASSWORD='test-password', DB_HOST='db.example.invalid',
        )
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(json.loads(valid.stdout)['sslmode'], 'require')

    def test_production_requires_hosts_and_callback_secret(self):
        db_vars = {
            'DEBUG': 'false', 'DB_ENGINE': 'postgresql', 'DB_NAME': 'ien',
            'DB_USER': 'ien', 'DB_PASSWORD': 'test-password',
            'DB_HOST': 'db.example.invalid',
        }
        no_hosts = self.run_settings(**db_vars, ALLOWED_HOSTS='')
        self.assertNotEqual(no_hosts.returncode, 0)
        self.assertIn('ALLOWED_HOSTS', no_hosts.stderr)

        no_hmac = self.run_settings(**db_vars, IA_CALLBACK_HMAC_SECRET='', IA_CALLBACK_TOKEN='')
        self.assertNotEqual(no_hmac.returncode, 0)
        self.assertIn('IA_CALLBACK_HMAC_SECRET', no_hmac.stderr)

    def test_production_rejects_modes_that_can_connect_without_tls(self):
        for mode in ('disable', 'allow', 'prefer'):
            with self.subTest(mode=mode):
                result = self.run_settings(
                    DEBUG='false', DB_ENGINE='postgresql', DB_NAME='ien',
                    DB_USER='ien', DB_PASSWORD='test-password',
                    DB_HOST='db.example.invalid', DB_SSLMODE=mode,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('DB_SSLMODE debe exigir TLS', result.stderr)

    def test_postgresql_rejects_unknown_sslmode(self):
        result = self.run_settings(
            DB_ENGINE='postgresql', DB_NAME='ien', DB_USER='ien',
            DB_PASSWORD='test-password', DB_HOST='localhost', DB_SSLMODE='typo',
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DB_SSLMODE', result.stderr)


if __name__ == '__main__':
    unittest.main()
