"""Detecta errores de despliegue antes de iniciar servicios reales."""

import unittest

from check_config import check_config


class DeploymentConfigTests(unittest.TestCase):
    def setUp(self):
        self.web = {
            'DEBUG': 'false', 'DB_ENGINE': 'postgresql', 'DB_NAME': 'ien',
            'DB_USER': 'ien', 'DB_PASSWORD': 'synthetic-db-password',
            'DB_HOST': '127.0.0.1', 'DB_SSLMODE': 'require',
            'SECRET_KEY': 'synthetic-secret', 'ALLOWED_HOSTS': 'bolsa.example.com,127.0.0.1',
            'CSRF_TRUSTED_ORIGINS': 'https://bolsa.example.com',
            'IA_API_TOKEN': 'synthetic-service', 'MATCH_API_TOKEN': 'synthetic-service',
            'IA_CALLBACK_HMAC_SECRET': 'synthetic-hmac',
            'CHANNEL_REDIS_URL': 'redis://127.0.0.1:6379/3',
            'IA_API_URL': 'http://127.0.0.1:8001/api/v1/cv-analyses',
            'IA_OFFER_API_URL': 'http://127.0.0.1:8001/api/v1/offer-analyses',
            'MATCH_API_URL': 'ws://127.0.0.1:8001/api/v1/ws/v1/matches',
            'MATCH_API_HTTP_URL': 'http://127.0.0.1:8001/api/v1',
            'TRUST_PROXY_HEADERS': 'true', 'SECURE_SSL_REDIRECT': 'true',
            'EMAIL_BACKEND': 'django.core.mail.backends.console.EmailBackend',
        }
        self.api = {
            'MODE': 'production', 'SERVICE_API_TOKEN': 'synthetic-service',
            'CV_RESULT_CALLBACK_HMAC_SECRET': 'synthetic-hmac',
            'CV_RESULT_CALLBACK_URL': 'http://127.0.0.1:8080/ia/llegue/',
            'CHANNEL_REDIS_URL': self.web['CHANNEL_REDIS_URL'],
            'LLM_PROVIDER': 'gemini', 'MATCH_PROVIDER': 'groq',
            'GEMINI_API_KEY': 'synthetic-gemini', 'GROQ_API_KEY': 'synthetic-groq',
        }

    def test_valid_production_configuration(self):
        self.assertEqual(check_config(self.web, self.api), [])

    def test_wrong_callback_port_is_detected(self):
        self.api['CV_RESULT_CALLBACK_URL'] = 'http://127.0.0.1:8000/ia/llegue/'
        self.assertTrue(any('callback' in error for error in check_config(self.web, self.api)))

    def test_mismatched_secrets_are_reported_without_values(self):
        self.api['SERVICE_API_TOKEN'] = 'different-synthetic-secret'
        errors = check_config(self.web, self.api)
        self.assertTrue(any('No coinciden' in error for error in errors))
        self.assertNotIn('different-synthetic-secret', str(errors))

    def test_smtp_credentials_are_required_for_email_delivery(self):
        self.web['EMAIL_BACKEND'] = 'django.core.mail.backends.smtp.EmailBackend'
        self.assertTrue(any('EMAIL_HOST_PASSWORD' in error for error in check_config(self.web, self.api)))

    def test_callback_host_must_be_allowed(self):
        self.web['ALLOWED_HOSTS'] = 'bolsa.example.com'
        self.assertTrue(any('ALLOWED_HOSTS' in error for error in check_config(self.web, self.api)))
