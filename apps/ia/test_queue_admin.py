from unittest.mock import patch
from types import SimpleNamespace

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse

from ia.models import TrabajoExtraccion
from ia.queue_monitor import remote_status


class QueueAdminTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.superuser = users.objects.create_superuser(email='queue-admin@example.test', password='testpass-42')
        self.staff = users.objects.create_user(email='queue-staff@example.test', password='testpass-42', is_staff=True)
        self.job = TrabajoExtraccion.objects.create(tipo='candidate_cv', clave_idempotencia='queue-test', source_hash='a'*64, remote_job_id='remote-123')
        self.url = reverse('admin:ia_trabajoextraccion_changelist')
        self.status_url = reverse('admin:ia_cv_queue_status', args=[self.job.pk])

    def test_only_superuser_can_open_monitor_and_status(self):
        for user in (None, self.staff):
            if user:
                self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 302)
            self.assertEqual(self.client.get(self.status_url).status_code, 302)
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, 'Cola de CV')
        self.assertContains(response, self.status_url)
        self.assertContains(self.client.get(reverse('admin:index')), 'Abrir cola de CV')

    @patch('ia.admin.remote_status', return_value={'status': 'rate_limited', 'message': 'Esperando capacidad o cuota'})
    def test_status_is_readonly_and_other_job_types_are_hidden(self, remote):
        self.client.force_login(self.superuser)
        response = self.client.get(self.status_url)
        self.assertEqual(response.json()['status'], 'rate_limited')
        self.assertIn('no-store', response['Cache-Control'])
        self.job.refresh_from_db()
        self.assertEqual(self.job.estado, 'pending')
        self.job.tipo = 'job_offer'
        self.job.save()
        self.assertEqual(self.client.get(self.status_url).status_code, 404)
        self.assertEqual(remote.call_count, 1)

    def test_queue_cannot_add_delete_or_change_jobs(self):
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.post(reverse('admin:ia_trabajoextraccion_add'), {}).status_code, 403)
        self.assertEqual(self.client.post(reverse('admin:ia_trabajoextraccion_delete', args=[self.job.pk]), {'post': 'yes'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('admin:ia_trabajoextraccion_change', args=[self.job.pk]), {'estado': 'completed'}).status_code, 403)


@override_settings(IA_API_URL='http://llm.test/api/v1/cv-analyses', IA_API_TOKEN='private-test-token')
class RemoteMonitorTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.job = SimpleNamespace(pk=42, remote_job_id='remote-123')

    @patch('ia.queue_monitor.requests.get')
    def test_reads_only_progress_and_caches_without_exposing_cv_or_token(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = {'status': 'rate_limited', 'completed_packets': 1, 'total_packets': 3, 'retry_after_seconds': 40, 'result': {'secret': 'CV-content'}, 'error': 'private-test-token'}
        result = remote_status(self.job)
        self.assertEqual(result['completed_packets'], 1)
        self.assertNotIn('result', result)
        self.assertNotIn('error', result)
        self.assertNotIn('private-test-token', str(result))
        self.assertEqual(remote_status(self.job), result)
        get.assert_called_once_with('http://llm.test/api/v1/cv-analyses/remote-123', headers={'Authorization': 'Bearer private-test-token'}, timeout=(2, 3), allow_redirects=False)

    @patch('ia.queue_monitor.requests.get', side_effect=requests.Timeout)
    def test_timeout_does_not_mark_job_failed(self, get):
        self.assertEqual(remote_status(self.job)['status'], 'unavailable')

    @patch('ia.queue_monitor.requests.get')
    def test_old_api_without_progress_fields_is_supported(self, get):
        get.return_value.status_code = 200
        get.return_value.json.return_value = {'status': 'completed', 'delivered': False}
        self.assertEqual(remote_status(self.job)['message'], 'Análisis terminado; entrega pendiente')
