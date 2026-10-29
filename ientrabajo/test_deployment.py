"""Regresiones de persistencia privada, disponibilidad y correo de despliegue."""

from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.db import DatabaseError
from django.test import SimpleTestCase, TestCase, override_settings
from redis import ConnectionError as RedisConnectionError

from ia.models import PrivateCVStorage
from ientrabajo.database import postgres_url_values
from ientrabajo.email_backends import BrevoEmailBackend


class PostgresURLTests(SimpleTestCase):
    def test_decodes_credentials_without_changing_environment(self):
        values = postgres_url_values('postgresql://user%40ien:p%40ss%2Fword@neon.invalid/demo%20db?sslmode=require&channel_binding=require')
        self.assertEqual(values['DB_USER'], 'user@ien')
        self.assertEqual(values['DB_PASSWORD'], 'p@ss/word')
        self.assertEqual(values['DB_NAME'], 'demo db')
        self.assertEqual(values['DB_CHANNEL_BINDING'], 'require')

    def test_invalid_urls_never_disclose_credentials(self):
        for url in ('mysql://user:secret@db/demo', 'postgresql://user:secret@db:bad/demo'):
            with self.subTest(url=url), self.assertRaises(RuntimeError) as error:
                postgres_url_values(url)
            self.assertNotIn('secret', str(error.exception))


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
    'private_cv': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
})
class PrivateRemoteStorageTests(SimpleTestCase):
    def test_private_file_roundtrip_and_deletion(self):
        storage = PrivateCVStorage()
        name = storage.save('demo.txt', ContentFile(b'CV ficticio'))
        self.addCleanup(storage.delete, name)
        self.assertTrue(storage.exists(name))
        self.assertEqual(storage.size(name), 11)
        with storage.open(name) as stored:
            self.assertEqual(stored.read(), b'CV ficticio')
        self.assertFalse(default_storage.exists(name))
        with self.assertRaises(ValueError):
            storage.url(name)
        storage.delete(name)
        self.assertFalse(storage.exists(name))

    @override_settings(STORAGES={
        'private_cv': {'BACKEND': 'storages.backends.s3.S3Storage', 'OPTIONS': {
            'bucket_name': 'test-private', 'access_key': 'fake', 'secret_key': 'fake',
            'endpoint_url': 'https://storage.example.invalid', 'region_name': 'us-east-1',
            'location': 'private/cv',
        }},
    })
    def test_s3_cv_has_no_local_path_or_download_url(self):
        storage = PrivateCVStorage()
        with self.assertRaises(NotImplementedError):
            storage.path('demo.txt')
        with self.assertRaises(ValueError):
            storage.url('demo.txt')


class HealthTests(TestCase):
    @patch('ientrabajo.health.Redis.from_url')
    def test_available(self, redis):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        redis.return_value.__enter__.return_value.ping.assert_called_once()
        self.assertIn('no-store', response['Cache-Control'])

    @patch('ientrabajo.health.Redis.from_url', side_effect=RedisConnectionError('host:secret'))
    def test_redis_failure_is_503_and_does_not_disclose_details(self, redis):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'unavailable'})

    @patch('ientrabajo.health.connection.cursor', side_effect=DatabaseError('credentials'))
    def test_database_failure_is_503(self, cursor):
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, 'credentials', status_code=503)


@override_settings(BREVO_API_KEY='test-only', EMAIL_TIMEOUT=15)
class HTTPEmailTests(SimpleTestCase):
    @patch('ientrabajo.email_backends.requests.post', return_value=Mock(status_code=201))
    def test_password_reset_message_keeps_text_html_and_recipients(self, post):
        message = EmailMultiAlternatives('Recuperar contraseña', 'Enlace de prueba',
                                        'IEN <demo@example.com>', ['persona@example.com'],
                                        bcc=['auditoria@example.com'])
        message.attach_alternative('<p>Enlace de prueba</p>', 'text/html')
        self.assertEqual(BrevoEmailBackend().send_messages([message]), 1)
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['sender'], {'name': 'IEN', 'email': 'demo@example.com'})
        self.assertEqual(payload['textContent'], 'Enlace de prueba')
        self.assertEqual(payload['htmlContent'], '<p>Enlace de prueba</p>')
        self.assertEqual(payload['bcc'], [{'email': 'auditoria@example.com'}])

    @patch('ientrabajo.email_backends.requests.post', return_value=Mock(status_code=429))
    def test_provider_rejection_is_not_counted_as_delivery(self, post):
        message = EmailMultiAlternatives('Prueba', 'Texto', 'demo@example.com', ['persona@example.com'])
        self.assertEqual(BrevoEmailBackend(fail_silently=True).send_messages([message]), 0)
        from smtplib import SMTPException
        with self.assertRaises(SMTPException):
            BrevoEmailBackend().send_messages([message])


class SupervisorTests(SimpleTestCase):
    @patch('deploy.start.signal.signal')
    @patch('deploy.start.subprocess.run')
    @patch('deploy.start.subprocess.Popen')
    def test_failed_dispatcher_stops_remaining_processes(self, popen, run, signal):
        from deploy.start import run as start
        children = [Mock(), Mock(), Mock()]
        children[0].poll.return_value = None
        children[1].poll.return_value = 1
        children[2].poll.return_value = None
        popen.side_effect = children
        self.assertEqual(start(), 1)
        children[0].terminate.assert_called_once()
        children[2].terminate.assert_called_once()

    @patch('deploy.start.signal.signal')
    @patch('deploy.start.subprocess.run')
    @patch('deploy.start.subprocess.Popen')
    def test_partial_startup_does_not_leave_an_orphan_process(self, popen, run, signal):
        from deploy.start import run as start
        child = Mock()
        child.poll.return_value = None
        popen.side_effect = [child, OSError('No se pudo iniciar')]
        with self.assertRaises(OSError):
            start()
        child.terminate.assert_called_once()
