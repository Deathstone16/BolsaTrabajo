from unittest.mock import patch
import requests
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from usuarios.models import Usuario


@override_settings(IA_API_URL='http://llm.test/api/v1/cv-analyses',IA_API_TOKEN='synthetic-private-token')
class TokenMonitorTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin=Usuario.objects.create_superuser(email='tokens-admin@example.invalid',password='synthetic-password')
        self.staff=Usuario.objects.create_user(email='tokens-staff@example.invalid',password='synthetic-password',is_staff=True)
        self.page=reverse('admin:ia_tokens');self.data=reverse('admin:ia_tokens_data')

    @patch('ia.token_monitor.requests.get')
    def test_staff_and_anonymous_cannot_see_or_query_usage(self,get):
        for user in (None,self.staff):
            if user:self.client.force_login(user)
            self.assertEqual(self.client.get(self.page).status_code,302)
            self.assertEqual(self.client.get(self.data).status_code,302)
        get.assert_not_called()

    @patch('ia.token_monitor.requests.get')
    def test_superadmin_page_and_proxy_never_expose_service_token(self,get):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.page),'Consumo de tokens')
        self.assertContains(self.client.get(reverse('admin:index')),'Ver consumo de tokens')
        get.return_value.status_code=200
        get.return_value.json.return_value={'totals':{'total_tokens':123},'models':[],'hours':[],'routes':[],
                                           'private_payload':'CV contents','authorization':'synthetic-private-token'}
        response=self.client.get(self.data)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['totals']['total_tokens'],123)
        self.assertNotContains(response,'synthetic-private-token')
        self.assertNotContains(response,'private_payload')
        self.client.get(self.data)
        get.assert_called_once_with('http://llm.test/api/v1/llm-usage',headers={'Authorization':'Bearer synthetic-private-token'},timeout=(2,5),allow_redirects=False)

    @patch('ia.token_monitor.requests.get',side_effect=requests.Timeout('sensitive internal address'))
    def test_outage_is_readonly_and_does_not_expose_internal_errors(self,get):
        self.client.force_login(self.admin)
        response=self.client.get(self.data)
        self.assertEqual(response.status_code,503)
        self.assertNotContains(response,'sensitive internal address',status_code=503)
