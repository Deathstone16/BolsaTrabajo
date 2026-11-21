from unittest.mock import Mock, patch

from django.core import mail
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings

from .mail import send_mail


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   IEN_PUBLIC_URL='http://127.0.0.1:8000', IEN_EMAIL_LOGO_URL='')
class BrandedMailTests(SimpleTestCase):
    def html(self):
        return render_to_string('emails/reset_email.html', {
            'usuario': {'email': 'demo@example.com'}, 'link': 'https://empleo.example.com/reset/',
        })

    def send(self):
        return send_mail('Prueba', 'Texto alternativo', 'ien@example.com', ['demo@example.com'], html_message=self.html())

    def test_smtp_message_is_html_without_image_attachments(self):
        self.assertEqual(self.send(), 1)
        message = mail.outbox[-1]
        self.assertEqual(message.body, 'Texto alternativo')
        html = message.alternatives[0].content
        self.assertIn('>IEN Trabajo</span>', html)
        self.assertNotIn('cid:', html)
        self.assertNotIn('127.0.0.1', html)
        self.assertEqual(message.attachments, [])
        self.assertEqual(message.message().get_content_type(), 'multipart/alternative')
        self.assertFalse(any(part.get_content_maintype() == 'image' for part in message.message().walk()))

    @override_settings(IEN_EMAIL_LOGO_URL='https://cdn.example.com/ien.png')
    def test_smtp_can_show_a_public_logo_without_attaching_it(self):
        self.assertEqual(self.send(), 1)
        message = mail.outbox[-1]
        self.assertIn('src="https://cdn.example.com/ien.png"', message.alternatives[0].content)
        self.assertEqual(message.attachments, [])

    @override_settings(EMAIL_BACKEND='ientrabajo.email_backends.BrevoEmailBackend', BREVO_API_KEY='test-only')
    @patch('ientrabajo.email_backends.requests.post', return_value=Mock(status_code=201))
    def test_http_backend_uses_text_brand_instead_of_broken_local_image(self, post):
        self.assertEqual(self.send(), 1)
        payload = post.call_args.kwargs['json']
        self.assertIn('>IEN Trabajo</span>', payload['htmlContent'])
        self.assertNotIn('cid:', payload['htmlContent'])
        self.assertNotIn('127.0.0.1', payload['htmlContent'])
        self.assertNotIn('attachment', payload)

    @override_settings(EMAIL_BACKEND='ientrabajo.email_backends.BrevoEmailBackend', BREVO_API_KEY='test-only',
                       IEN_EMAIL_LOGO_URL='https://cdn.example.com/ien.png')
    @patch('ientrabajo.email_backends.requests.post', return_value=Mock(status_code=201))
    def test_http_backend_uses_configured_public_logo(self, post):
        self.assertEqual(self.send(), 1)
        self.assertIn('src="https://cdn.example.com/ien.png"', post.call_args.kwargs['json']['htmlContent'])

    def test_rejection_reason_is_escaped(self):
        html = render_to_string('emails/perfil_rechazado.html', {'motivo_rechazo': '<script>alert(1)</script>'})
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
