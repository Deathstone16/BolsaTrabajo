from django.test import TestCase, override_settings
from django.urls import reverse
from usuarios.models import Usuario, Oferente
from usuarios.forms import LoginForm


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AuthFlowRegressionTests(TestCase):
    def company_data(self):
        return {'nombre_empresa':'Empresa de prueba','cuit':'20123456786','contacto_nombre':'Responsable',
                'contacto_cargo':'RRHH','correo_publico':'contact@example.invalid','email':'new-company@example.invalid',
                'password1':'Z8!clave-prueba-7235','password2':'Z8!clave-prueba-7235'}

    def test_new_company_redirects_to_clear_confirmation_and_creates_one_account(self):
        response=self.client.post(reverse('registro')+'?tipo=oferente',self.company_data(),follow=True)
        self.assertEqual(response.redirect_chain,[(reverse('registro_exitoso')+'?tipo=oferente',302)])
        self.assertContains(response,'Tu empresa quedó en revisión')
        self.assertIn('no-store',response['Cache-Control'])
        self.assertEqual(Usuario.objects.filter(email='new-company@example.invalid').count(),1)
        company=Oferente.objects.get(usuario__email='new-company@example.invalid')
        self.assertEqual(company.estado_validacion,'pendiente')

    def test_duplicate_email_is_rejected_with_next_action_without_changing_password(self):
        self.client.post(reverse('registro')+'?tipo=oferente',self.company_data())
        response=self.client.post(reverse('registro')+'?tipo=oferente',self.company_data())
        self.assertContains(response,'Este correo ya tiene una cuenta.')
        self.assertEqual(Usuario.objects.filter(email='new-company@example.invalid').count(),1)
        self.assertTrue(Usuario.objects.get(email='new-company@example.invalid').check_password(self.company_data()['password1']))

    def test_login_keeps_password_spaces_and_redirects_authenticated_browser(self):
        password=' Z8!clave-prueba-7235 '
        user=Usuario.objects.create_user(email='login-flow@example.invalid',password=password)
        form=LoginForm({'email':user.email,'password':password})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['password'],password)
        response=self.client.post(reverse('login'),{'email':user.email,'password':password})
        self.assertRedirects(response,reverse('home'),fetch_redirect_response=False)
        self.assertEqual(self.client.session['_auth_user_id'],str(user.pk))
        response=self.client.get(reverse('login'))
        self.assertRedirects(response,reverse('home'),fetch_redirect_response=False)
        self.assertIn('no-store',response['Cache-Control'])

    def test_repeated_same_form_returns_confirmation_instead_of_duplicate_error(self):
        page=self.client.get(reverse('registro')+'?tipo=oferente')
        data={**self.company_data(), 'registration_attempt':page.context['registration_attempt']}
        first=self.client.post(reverse('registro')+'?tipo=oferente',data)
        second=self.client.post(reverse('registro')+'?tipo=oferente',data)
        self.assertEqual(first.status_code,302)
        self.assertEqual(second.status_code,302)
        self.assertEqual(first.url,second.url)
        self.assertEqual(Usuario.objects.filter(email=data['email']).count(),1)
        another_page=self.client.get(reverse('registro')+'?tipo=oferente')
        different={**data,'registration_attempt':another_page.context['registration_attempt']}
        response=self.client.post(reverse('registro')+'?tipo=oferente',different)
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Este correo ya tiene una cuenta.')

    def test_retry_cannot_claim_success_with_different_password(self):
        page=self.client.get(reverse('registro')+'?tipo=oferente')
        data={**self.company_data(),'registration_attempt':page.context['registration_attempt']}
        self.client.post(reverse('registro')+'?tipo=oferente',data)
        response=self.client.post(reverse('registro')+'?tipo=oferente',{**data,'password1':'Another-strong-93!','password2':'Another-strong-93!'})
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Este correo ya tiene una cuenta.')

    def test_retry_cache_failure_does_not_break_successful_registration(self):
        from unittest.mock import patch
        page=self.client.get(reverse('registro')+'?tipo=oferente')
        data={**self.company_data(),'registration_attempt':page.context['registration_attempt']}
        with patch('usuarios.registration_attempts.cache.set',side_effect=RuntimeError('cache unavailable')):
            response=self.client.post(reverse('registro')+'?tipo=oferente',data)
        self.assertEqual(response.status_code,302)
        self.assertTrue(Usuario.objects.filter(email=data['email']).exists())
