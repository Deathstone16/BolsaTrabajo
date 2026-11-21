from django.contrib import admin
from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario


class TechnicalAdminAccessTests(TestCase):
    def setUp(self):
        self.staff = Usuario.objects.create_user(email='institute@example.com', password='Test-password-42', is_staff=True)
        self.superuser = Usuario.objects.create_superuser(email='technical@example.com', password='Test-password-42')

    def test_institute_staff_can_manage_platform_but_not_technical_admin(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('mod_listar_empresas')).status_code, 200)
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:login'), response.url)

    def test_staff_password_cannot_log_into_technical_admin(self):
        response = self.client.post(reverse('admin:login'), {'username': self.staff.email, 'password': 'Test-password-42', 'next': reverse('admin:index')})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_active_superuser_can_access_technical_admin(self):
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)

    def test_inactive_superuser_is_denied(self):
        self.superuser.is_active = False
        from django.test import RequestFactory
        request = RequestFactory().get(reverse('admin:index'))
        request.user = self.superuser
        self.assertFalse(admin.site.has_permission(request))

    def test_institute_sign_in_does_not_redirect_to_technical_admin(self):
        response = self.client.get(reverse('mod_listar_empresas'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login') + '?next='))

    def test_technical_admin_uses_configured_path(self):
        self.assertEqual(reverse('admin:index'), '/' + settings.DJANGO_ADMIN_PATH)
        if settings.DJANGO_ADMIN_PATH != 'admin/':
            self.assertEqual(self.client.get('/admin/').status_code, 404)
