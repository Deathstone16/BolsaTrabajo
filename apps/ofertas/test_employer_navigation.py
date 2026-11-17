from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

from usuarios.models import Oferente, Postulante, Usuario


class NavegacionOferenteTests(TestCase):
    def render_nav(self, user, path='/ofertas/dashboard/'):
        from django.urls import resolve
        request = RequestFactory().get(path)
        request.user = user
        request.resolver_match = resolve(path)
        return render_to_string('nueva_ui/partials/_nav.html', request=request)

    def crear_oferente(self, estado='aprobado'):
        user = Usuario.objects.create_user(email='menu@example.com')
        Oferente.objects.create(usuario=user, nombre_empresa='Empresa de prueba',
                               cuit='30-12345678-1', estado_validacion=estado)
        return user

    def test_menu_aprobado_tiene_las_mismas_acciones_en_escritorio_y_movil(self):
        html = self.render_nav(self.crear_oferente())
        for label in ('Mis ofertas', 'Publicar oferta', 'Mi empresa', 'Mi cuenta'):
            self.assertEqual(html.count('>' + label + '<') + html.count('> ' + label + '<'), 2)
        self.assertEqual(html.count('href="' + reverse('crear_oferta') + '"'), 2)
        self.assertEqual(html.count('<details class="ien-employer-account">'), 2)
        self.assertNotIn('>Inicio</a>', html)
        self.assertNotIn('>Cursos</a>', html)
        self.assertNotIn('>Mi panel</a>', html)
        self.assertNotIn('>Buscar empleo</a>', html)
        self.assertIn('aria-current="page">Mis ofertas', html)

    def test_empresa_pendiente_puede_editar_perfil_pero_no_publicar(self):
        html = self.render_nav(self.crear_oferente('pendiente'), reverse('validacion_pendiente'))
        self.assertIn('Estado de mi cuenta', html)
        self.assertIn('href="' + reverse('editar_perfil_empresa') + '"', html)
        self.assertNotIn('href="' + reverse('crear_oferta') + '"', html)

    def test_menu_visitante_y_postulante_conserva_opciones(self):
        anonymous = self.render_nav(AnonymousUser(), '/')
        self.assertIn('>Inicio</a>', anonymous)
        self.assertIn('>Cursos</a>', anonymous)
        self.assertIn('>Buscar empleo</a>', anonymous)
        self.assertNotIn('ien-employer-nav', anonymous)
        user = Usuario.objects.create_user(email='postulante-menu@example.com')
        Postulante.objects.create(usuario=user)
        candidate = self.render_nav(user, '/')
        self.assertIn('>Mi perfil</a>', candidate)
        self.assertIn('>Cursos</a>', candidate)
        self.assertNotIn('ien-employer-nav', candidate)
