from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.test import SimpleTestCase, RequestFactory, override_settings
from django.urls import path
from . import error_pages


def denied(request): raise PermissionDenied('private-reason')
def broken(request): raise RuntimeError('private-exception')
urlpatterns = [path('denied/', denied), path('broken/', broken)]
handler403 = 'ientrabajo.error_pages.permission_denied'
handler404 = 'ientrabajo.error_pages.not_found'
handler500 = 'ientrabajo.error_pages.server_error'


@override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'], ROOT_URLCONF=__name__)
class ErrorPageTests(SimpleTestCase):
    def test_exception_pages_have_correct_status_and_no_private_details(self):
        self.client.raise_request_exception = False
        for url, code in [('/missing/?token=secret-query', 404), ('/denied/', 403), ('/broken/', 500)]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, code)
            self.assertContains(response, 'bnf-bottle', status_code=code)
            for secret in ('secret-query', 'private-reason', 'private-exception', 'Traceback'):
                self.assertNotContains(response, secret, status_code=code)

    def test_error_pages_never_query_the_database(self):
        for code in (400, 403, 404, 500, 503, 504):
            response = error_pages.render_error(RequestFactory().get('/example/?token=secret'), code)
            self.assertEqual(response.status_code, code)
            self.assertEqual(response['Cache-Control'], 'no-store')
            self.assertNotContains(response, 'token=secret', status_code=code)

    def test_post_errors_offer_no_resubmit_link(self):
        response = error_pages.render_error(RequestFactory().post('/submit/', {'password': 'private-form'}), 504)
        self.assertNotContains(response, 'Volver a intentar', status_code=504)
        self.assertNotContains(response, 'private-form', status_code=504)

    def test_ajax_errors_keep_json_contract(self):
        request = RequestFactory().get('/api/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = error_pages.render_error(request, 500)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertJSONEqual(response.content, {'success': False, 'mensaje': error_pages.ERRORS[500][2]})

    def test_middleware_does_not_replace_json_or_success_responses(self):
        for original in (JsonResponse({'detail': 'service-error'}, status=503), HttpResponse('Normal content')):
            response = error_pages.ServerErrorPageMiddleware(lambda request: original)(RequestFactory().get('/'))
            self.assertEqual(response.content, original.content)

    def test_explicit_service_failure_gets_error_page_and_keeps_headers(self):
        original = HttpResponse('internal-details', status=503, headers={'Retry-After': '120'})
        response = error_pages.ServerErrorPageMiddleware(lambda request: original)(RequestFactory().get('/'))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Retry-After'], '120')
        self.assertContains(response, 'bnf-bottle', status_code=503)
        self.assertNotContains(response, 'internal-details', status_code=503)
