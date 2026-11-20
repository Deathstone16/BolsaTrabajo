from datetime import timedelta

from django.test import TestCase
from django.template.loader import render_to_string
from django.urls import reverse
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from categorias.models import Categoria
from ofertas.models import Oferta
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
                               cuit='30-12345678-1', estado_validacion=estado,
                               contacto_nombre='Responsable Demo', contacto_cargo='RRHH', correo_publico='rrhh@example.com')
        return user

    def test_estado_pendiente_no_habilita_publicar(self):
        self.client.force_login(self.crear_oferente('pendiente'))
        response = self.client.get(reverse('validacion_pendiente'))
        self.assertContains(response, 'Tu empresa está siendo revisada')
        self.assertContains(response, reverse('editar_perfil_empresa'))
        self.assertNotContains(response, 'href="' + reverse('crear_oferta') + '"')

    def test_rechazo_muestra_motivo_y_acceso_a_corregir(self):
        user = self.crear_oferente('rechazado')
        empresa = user.oferente
        empresa.motivo_rechazo = 'Verificá el CUIT <documento>'
        empresa.save(update_fields=['motivo_rechazo'])
        self.client.force_login(user)
        response = self.client.get(reverse('validacion_pendiente'))
        self.assertContains(response, 'Tu registro fue rechazado')
        self.assertContains(response, 'Verificá el CUIT &lt;documento&gt;')
        self.assertContains(response, 'Corregir datos y reenviar')
        self.assertNotContains(response, 'href="' + reverse('crear_oferta') + '"')

    def test_menu_aprobado_tiene_las_mismas_acciones_en_escritorio_y_movil(self):
        html = self.render_nav(self.crear_oferente())
        for label in ('Mis ofertas', 'Publicar oferta', 'Mi empresa', 'Mi cuenta'):
            esperado = 4 if label in ('Mis ofertas', 'Publicar oferta') else 2
            self.assertEqual(html.count('>' + label + '<') + html.count('> ' + label + '<'), esperado)
        self.assertEqual(html.count('href="' + reverse('crear_oferta') + '"'), 4)
        self.assertEqual(html.count('<details class="ien-employer-account">'), 2)
        self.assertNotIn('>Inicio</a>', html)
        self.assertNotIn('>Cursos</a>', html)
        self.assertNotIn('>Mi panel</a>', html)
        self.assertNotIn('>Buscar empleo</a>', html)
        self.assertIn('aria-current="page">Mis ofertas', html)

    def test_dropdown_oferente_incluye_perfil_edicion_y_gestion(self):
        user = self.crear_oferente()
        request = RequestFactory().get('/')
        request.user = user
        html = render_to_string('nueva_ui/partials/_account_options.html', request=request)
        for url in (reverse('perfil_oferente', args=[user.oferente.pk]),
                    reverse('editar_perfil_empresa'), reverse('dashboard_empresa'),
                    reverse('crear_oferta'), reverse('logout')):
            self.assertIn(url, html)
        self.assertNotIn(reverse('favoritos'), html)
        self.assertNotIn(reverse('mod_listar_empresas'), html)

    def test_dropdown_admin_incluye_toda_la_gestion(self):
        user = Usuario.objects.create_user(email='admin-menu@example.com', is_staff=True)
        request = RequestFactory().get('/')
        request.user = user
        html = render_to_string('nueva_ui/partials/_account_options.html', request=request)
        for name in ('mod_listar_empresas', 'mod_listar_ofertas', 'mod_listar_cursos',
                     'mod_listar_categorias', 'mod_solicitudes_empresas', 'logout'):
            self.assertIn(reverse(name), html)
        self.assertNotIn(reverse('admin:index'), html)
        self.assertNotIn(reverse('mi_perfil'), html)

    def test_dropdown_postulante_incluye_sus_secciones(self):
        user = Usuario.objects.create_user(email='dropdown-postulante@example.com')
        Postulante.objects.create(usuario=user)
        request = RequestFactory().get('/')
        request.user = user
        html = render_to_string('nueva_ui/partials/_account_options.html', request=request)
        for name in ('mi_perfil', 'ia:perfil_profesional', 'datos_personales', 'favoritos', 'logout'):
            self.assertIn(reverse(name), html)
        self.assertIn(reverse('mi_perfil') + '#cv-analysis', html)
        self.assertNotIn(reverse('mod_listar_empresas'), html)
        self.assertNotIn(reverse('crear_oferta'), html)

    def test_oferente_puede_ver_su_perfil_pero_no_el_de_otra_empresa(self):
        user = self.crear_oferente()
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse('perfil_oferente', args=[user.oferente.pk])), user.oferente.nombre_empresa)
        otro = Usuario.objects.create_user(email='otra-empresa-menu@example.com')
        empresa = Oferente.objects.create(usuario=otro, nombre_empresa='Otra empresa', cuit='30-12345678-1')
        self.assertRedirects(self.client.get(reverse('perfil_oferente', args=[empresa.pk])), reverse('home'))

    def test_empresa_pendiente_puede_editar_perfil_pero_no_publicar(self):
        html = self.render_nav(self.crear_oferente('pendiente'), reverse('validacion_pendiente'))
        self.assertIn('Estado de mi cuenta', html)
        self.assertIn('href="' + reverse('editar_perfil_empresa') + '"', html)
        self.assertNotIn('href="' + reverse('crear_oferta') + '"', html)

    def test_dashboard_alterna_entre_primera_oferta_y_nueva_oferta(self):
        user = self.crear_oferente()
        self.client.force_login(user)

        vacio = self.client.get(reverse('dashboard_empresa'))
        self.assertContains(vacio, 'Publicar primera oferta')
        self.assertNotContains(vacio, 'Nueva oferta')

        Oferta.objects.create(
            empresa=user,
            categoria=Categoria.objects.create(nombre='Tecnología'),
            titulo='Oferta inicial',
            nombre_puesto='Desarrollador',
            ubicacion='Córdoba',
            descripcion='Descripción de prueba',
            habilidades_requeridas='Python',
            nivel_educativo='universitario',
            fecha_cierre=timezone.now() + timedelta(days=10),
        )
        con_oferta = self.client.get(reverse('dashboard_empresa'))
        self.assertContains(con_oferta, 'Nueva oferta')
        self.assertNotContains(con_oferta, 'Publicar primera oferta')

    def test_empresa_aprobada_con_responsable_incompleto_debe_editar_perfil(self):
        user = Usuario.objects.create_user(email='legacy-sin-responsable@example.com')
        Oferente.objects.create(
            usuario=user, nombre_empresa='Empresa legacy', cuit='30-12345678-1',
            estado_validacion=Oferente.EstadoValidacion.APROBADO,
            contacto_nombre='Responsable de prueba',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('crear_oferta'))

        self.assertRedirects(response, reverse('editar_perfil_empresa'))

    def test_menu_visitante_y_postulante_conserva_opciones(self):
        anonymous = self.render_nav(AnonymousUser(), '/')
        self.assertIn('>Inicio</a>', anonymous)
        self.assertIn('>Cursos</a>', anonymous)
        self.assertIn('>Buscar empleo</a>', anonymous)
        self.assertNotIn('ien-employer-nav', anonymous)
        user = Usuario.objects.create_user(email='postulante-menu@example.com', first_name='Benjamín')
        Postulante.objects.create(usuario=user)
        candidate = self.render_nav(user, '/')
        self.assertEqual(candidate.count('> Mi perfil</a>'), 2)
        self.assertEqual(candidate.count('> Favoritos</a>'), 2)
        self.assertIn('>Cursos</a>', candidate)
        self.assertNotIn('ien-employer-nav', candidate)
        self.assertIn('/img/ien-trabajo', candidate)
        self.assertIn('alt="ien trabajo"', candidate)
        self.assertNotIn('>Postulante<', candidate)
        self.assertEqual(candidate.count('aria-label="Menú de mi cuenta"'), 2)
        self.assertEqual(candidate.count('> Cerrar sesión</button>'), 2)
        self.assertIn('class="ien-header-user-name">Benjamín</span>', candidate)
        self.assertNotIn('Bolsa de trabajo · Chaco', candidate)
