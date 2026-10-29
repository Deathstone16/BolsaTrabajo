from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from ofertas.models import Oferta
from usuarios.models import Oferente, Usuario
from usuarios.admin import OferenteAdmin

from .services import listar_empresas_contexto


class ModeracionOfertasTests(TestCase):
    def setUp(self):
        self.staff = Usuario.objects.create_user(
            email='moderador@example.com', password='clave-segura', is_staff=True,
        )
        empresa = Usuario.objects.create_user(
            email='empresa-moderada@example.com', password='clave-segura',
        )
        Oferente.objects.create(
            usuario=empresa,
            nombre_empresa='Empresa de prueba',
            cuit='30-12345678-9',
            estado_validacion=Oferente.EstadoValidacion.APROBADO,
        )
        categoria = Categoria.objects.create(nombre='Tecnología')
        self.oferta = Oferta.objects.create(
            empresa=empresa,
            categoria=categoria,
            titulo='Desarrollador', nombre_puesto='Desarrollador',
            ubicacion='Córdoba', descripcion='Descripción de prueba',
            habilidades_requeridas='Python', habilidades_duras='Python',
            requisitos_obligatorios='Python',
            requisitos_estructurados=[{
                'id': 'fixture-python', 'category': 'technical_skills',
                'source': 'requisitos_obligatorios', 'name': 'Python',
                'mandatory': True, 'exclusionary': False,
            }],
            requiere_revision_requisitos=False,
            nivel_educativo='universitario',
            fecha_cierre=timezone.now() + timedelta(days=10),
        )

    def test_detalle_oferta_requiere_staff(self):
        response = self.client.get(reverse('mod_detalle_oferta', args=[self.oferta.id]))
        self.assertEqual(response.status_code, 302)

    def test_detalle_oferta_muestra_datos(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('mod_detalle_oferta', args=[self.oferta.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Desarrollador')
        self.assertContains(response, 'Empresa de prueba')

    def test_aprobar_oferta_redirige_y_activa(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('mod_aprobar_oferta', args=[self.oferta.id]))
        self.assertEqual(response.status_code, 302)
        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.estado, 'activa')

    def test_no_publica_una_oferta_legacy_hasta_que_se_revisen_requisitos(self):
        self.oferta.requiere_revision_requisitos = True
        self.oferta.save(update_fields=['requiere_revision_requisitos'])
        self.client.force_login(self.staff)
        response = self.client.post(reverse('mod_aprobar_oferta', args=[self.oferta.id]))
        self.assertEqual(response.status_code, 302)
        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.estado, 'pendiente')

    def test_rechazo_exige_motivo(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('mod_rechazar_oferta', args=[self.oferta.id]))
        self.assertEqual(response.status_code, 200)
        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.estado, 'pendiente')

    def test_rechazo_guarda_motivo(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse('mod_rechazar_oferta', args=[self.oferta.id]),
            {'motivo': 'Datos incompletos'},
        )
        self.assertEqual(response.status_code, 302)
        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.estado, 'rechazada')
        self.assertEqual(self.oferta.motivo_rechazo, 'Datos incompletos')

    def test_finalizar_oferta_redirige_y_finaliza(self):
        self.client.force_login(self.staff)
        self.oferta.aprobar()
        response = self.client.post(reverse('mod_finalizar_oferta', args=[self.oferta.id]))
        self.assertEqual(response.status_code, 302)
        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.estado, 'finalizada')

    def test_total_empresas_pendientes_usa_estado_real(self):
        usuario = Usuario.objects.create_user(email='pendiente@example.com', password='clave-segura')
        Oferente.objects.create(
            usuario=usuario,
            nombre_empresa='Empresa pendiente',
            cuit='30-12345678-9',
        )

        contexto = listar_empresas_contexto()

        self.assertEqual(contexto['total'], 1)

    def test_empresa_aprobada_ve_estado_validado_en_su_panel(self):
        empresa = Oferente.objects.get(nombre_empresa='Empresa de prueba')
        self.client.force_login(empresa.usuario)

        response = self.client.get(reverse('dashboard_empresa'))

        self.assertContains(response, 'Empresa Validada')

    def test_empresa_aprobada_no_ve_pantalla_pendiente(self):
        empresa = Oferente.objects.get(nombre_empresa='Empresa de prueba')
        self.client.force_login(empresa.usuario)

        response = self.client.get(reverse('validacion_pendiente'))

        self.assertRedirects(response, reverse('dashboard_empresa'))

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='notificaciones@example.com',
        IEN_CONTACT_EMAIL='contacto@example.com',
    )
    def test_aprobar_empresa_envia_un_solo_correo_con_enlace_real(self):
        usuario = Usuario.objects.create_user(email='pendiente@example.com', password='clave-segura')
        empresa = Oferente.objects.create(
            usuario=usuario, nombre_empresa='Empresa pendiente', cuit='30-12345678-9',
        )
        self.client.force_login(self.staff)
        url = reverse('mod_aprobar_empresa', args=[empresa.pk])

        self.assertEqual(self.client.post(url).status_code, 302)
        empresa.refresh_from_db()
        self.assertEqual(empresa.estado_validacion, Oferente.EstadoValidacion.APROBADO)
        self.assertEqual(len(mail.outbox), 1)
        mensaje = mail.outbox[0]
        self.assertEqual(mensaje.to, [usuario.email])
        self.assertIn('http://testserver' + reverse('dashboard_empresa'), mensaje.body)
        html = mensaje.alternatives[0].content
        self.assertIn('http://testserver' + reverse('dashboard_empresa'), html)
        self.assertIn('#F8F3F0', html)
        self.assertIn('#512DA8', html)
        self.assertIn('#FFDE59', html)
        self.assertIn('Bolsa de trabajo &middot; Chaco', html)
        self.assertNotIn('tusitio.com', html)
        self.assertNotIn('✅', html)
        self.assertNotIn('🎯', html)

        self.client.post(url)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_fallo_smtp_no_revierte_aprobacion_ni_reenvia_en_reintento(self):
        usuario = Usuario.objects.create_user(email='sin-smtp@example.com', password='clave-segura')
        empresa = Oferente.objects.create(
            usuario=usuario, nombre_empresa='Empresa sin SMTP', cuit='30-12345678-9',
        )
        self.client.force_login(self.staff)
        url = reverse('mod_aprobar_empresa', args=[empresa.pk])

        with patch('usuarios.services.send_mail', side_effect=OSError('SMTP no disponible')) as envio, \
                patch('moderacion.views.logger') as logger:
            self.assertEqual(self.client.post(url).status_code, 302)
            self.client.post(url)

        empresa.refresh_from_db()
        self.assertEqual(empresa.estado_validacion, Oferente.EstadoValidacion.APROBADO)
        envio.assert_called_once()
        logger.exception.assert_called_once()

    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
        DEFAULT_FROM_EMAIL='notificaciones@example.com',
    )
    def test_aprobacion_desde_admin_notifica_solo_al_cambiar_de_estado(self):
        usuario = Usuario.objects.create_user(email='admin-empresa@example.com', password='clave-segura')
        empresa = Oferente.objects.create(
            usuario=usuario, nombre_empresa='Empresa administrada', cuit='30-12345678-9',
        )
        request = RequestFactory().post('/admin/usuarios/oferente/')
        request.user = self.staff
        administrador = OferenteAdmin(Oferente, admin.site)
        empresa.estado_validacion = Oferente.EstadoValidacion.APROBADO

        with self.captureOnCommitCallbacks(execute=True):
            administrador.save_model(request, empresa, form=None, change=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(reverse('dashboard_empresa'), mail.outbox[0].body)

        with self.captureOnCommitCallbacks(execute=True):
            administrador.save_model(request, empresa, form=None, change=True)
        self.assertEqual(len(mail.outbox), 1)
