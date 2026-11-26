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
