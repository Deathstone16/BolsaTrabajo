from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from usuarios.models import Oferente, Usuario
from usuarios import services as usuarios_services
from .models import SolicitudEmpresa, ControlRecordatorios
from .reminders import enviar_recordatorios_empresas


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='notificaciones@example.com', IEN_REVIEW_EMAILS=['admin@example.com'],
    IEN_COMPANY_REMINDER_HOURS=24, IEN_PUBLIC_URL='https://empleo.example.com',
)
class RecordatoriosEmpresasTests(TestCase):
    def empresa(self, nombre='Empresa de prueba'):
        user = Usuario.objects.create_user(email=f'empresa-{Usuario.objects.count()}@example.com')
        return Oferente.objects.create(usuario=user, nombre_empresa=nombre, cuit='30-12345678-1')

    def vencer(self, empresa):
        SolicitudEmpresa.objects.filter(empresa=empresa).update(recordar_desde=timezone.now() - timedelta(minutes=1))

    def test_registro_crea_alerta_sin_enviar_correo_ni_duplicar_al_guardar(self):
        user = usuarios_services.registrar_oferente('nueva@example.com', 'clave', 'Nueva', '30-12345678-1')
        solicitud = SolicitudEmpresa.objects.get(empresa=user.oferente)
        self.assertAlmostEqual((solicitud.recordar_desde - solicitud.creada_en).total_seconds(), 86400, delta=2)
        user.oferente.save()
        self.assertEqual(SolicitudEmpresa.objects.count(), 1)
        self.assertEqual(enviar_recordatorios_empresas(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_vencidas_se_agrupan_en_un_correo_y_no_se_repiten(self):
        una, otra, nueva = self.empresa('Una'), self.empresa('Otra'), self.empresa('Nueva')
        self.vencer(una)
        self.vencer(otra)
        self.assertEqual(enviar_recordatorios_empresas(), 2)
        self.assertEqual(len(mail.outbox), 1)
        mensaje = mail.outbox[0]
        self.assertEqual(mensaje.to, ['admin@example.com'])
        self.assertIn('Una', mensaje.body)
        self.assertIn('Otra', mensaje.body)
        self.assertNotIn('Nueva', mensaje.body)
        self.assertIn('https://empleo.example.com' + reverse('mod_solicitudes_empresas'), mensaje.body)
        self.assertEqual(enviar_recordatorios_empresas(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIsNone(SolicitudEmpresa.objects.get(empresa=nueva).recordatorio_enviado_en)

    def test_resueltas_antes_del_plazo_no_generan_recordatorio(self):
        empresa = self.empresa()
        self.vencer(empresa)
        usuarios_services.aprobar_empresa(empresa)
        solicitud = SolicitudEmpresa.objects.get(empresa=empresa)
        self.assertEqual(solicitud.estado, 'aprobado')
        self.assertIsNotNone(solicitud.resuelta_en)
        self.assertEqual(enviar_recordatorios_empresas(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_reenvio_genera_nueva_solicitud_con_nuevo_plazo(self):
        empresa = self.empresa()
        # Se obtiene otra instancia para reproducir una nueva petición de moderación.
        empresa = Oferente.objects.get(pk=empresa.pk)
        usuarios_services.rechazar_empresa(empresa, 'Revisar datos')
        usuarios_services.enviar_a_revision(empresa)
        self.assertEqual(SolicitudEmpresa.objects.filter(empresa=empresa).count(), 2)
        self.assertEqual(SolicitudEmpresa.objects.filter(empresa=empresa, resuelta_en__isnull=True).count(), 1)
        self.assertEqual(SolicitudEmpresa.objects.filter(empresa=empresa, estado='rechazado').count(), 1)

    def test_fallo_smtp_conserva_pendientes_para_reintento(self):
        empresa = self.empresa()
        self.vencer(empresa)
        with patch('moderacion.reminders.send_mail', side_effect=OSError('fallo SMTP')), patch('moderacion.reminders.logger'):
            self.assertEqual(enviar_recordatorios_empresas(), 0)
        self.assertIsNone(SolicitudEmpresa.objects.get(empresa=empresa).recordatorio_enviado_en)
        control = ControlRecordatorios.objects.get()
        self.assertIsNone(control.reservado_hasta)
        self.assertGreater(control.proximo_envio_en, timezone.now())
        ControlRecordatorios.objects.update(proximo_envio_en=timezone.now() - timedelta(seconds=1))
        self.assertEqual(enviar_recordatorios_empresas(), 1)

    def test_un_proceso_reservado_o_cooldown_evitan_otro_envio(self):
        empresa = self.empresa()
        self.vencer(empresa)
        ControlRecordatorios.objects.create(reservado_hasta=timezone.now() + timedelta(minutes=2))
        self.assertEqual(enviar_recordatorios_empresas(), 0)
        ControlRecordatorios.objects.update(reservado_hasta=timezone.now() - timedelta(minutes=1))
        self.assertEqual(enviar_recordatorios_empresas(), 1)
        otra = self.empresa('Otra')
        self.vencer(otra)
        self.assertEqual(enviar_recordatorios_empresas(), 0)
        ControlRecordatorios.objects.update(proximo_envio_en=timezone.now() - timedelta(seconds=1))
        self.assertEqual(enviar_recordatorios_empresas(), 1)
        self.assertEqual(len(mail.outbox), 2)

    @override_settings(IEN_REVIEW_EMAILS=[])
    def test_sin_destinatario_explicito_usa_solo_staff_activo(self):
        Usuario.objects.create_user(email='staff@example.com', is_staff=True)
        Usuario.objects.create_user(email='inactivo@example.com', is_staff=True, is_active=False)
        empresa = self.empresa()
        self.vencer(empresa)
        self.assertEqual(enviar_recordatorios_empresas(), 1)
        self.assertEqual(mail.outbox[0].to, ['staff@example.com'])

    def test_historial_campana_y_permisos(self):
        empresa = self.empresa('Empresa para revisar')
        admin = Usuario.objects.create_user(email='staff@example.com', is_staff=True)
        self.client.force_login(admin)
        url = reverse('mod_solicitudes_empresas')
        response = self.client.get(url)
        self.assertContains(response, 'Empresa para revisar')
        self.assertContains(response, 'Solicitudes de empresas: 1 pendiente')
        self.assertContains(response, 'Catálogo')
        self.assertNotContains(response, '>Inicio</a>')
        self.assertNotContains(response, '>Gestionar cursos</a>')
        usuarios_services.aprobar_empresa(empresa)
        self.assertContains(self.client.get(url + '?estado=aprobado'), 'Empresa para revisar')
        filtered = self.client.get(url + '?estado=pendiente')
        self.assertEqual(list(filtered.context['pagina']), [])
        self.client.force_login(empresa.usuario)
        self.assertNotEqual(self.client.get(url).status_code, 200)
        self.assertNotContains(self.client.get(reverse('home')), 'ien-admin-bell')

    def test_actualizacion_de_campana_es_privada_y_refleja_resoluciones(self):
        empresa = self.empresa('Alerta nueva')
        admin = Usuario.objects.create_user(email='admin-poll@example.com', is_staff=True)
        self.client.force_login(admin)
        url = reverse('mod_notificaciones_empresas')
        response = self.client.get(url)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.json()['pendientes'], 1)
        self.assertEqual(response.json()['recientes'][0]['empresa'], 'Alerta nueva')
        usuarios_services.aprobar_empresa(empresa)
        self.assertEqual(self.client.get(url).json()['pendientes'], 0)
        self.assertEqual(self.client.get(url).json()['recientes'][0]['estado'], 'Aprobada')
        self.client.force_login(empresa.usuario)
        self.assertEqual(self.client.get(url).status_code, 302)

    @override_settings(IEN_PUBLIC_URL='')
    def test_sin_url_publica_no_se_envian_enlaces_rotos(self):
        empresa = self.empresa()
        self.vencer(empresa)
        with patch('moderacion.reminders.logger'):
            self.assertEqual(enviar_recordatorios_empresas(), 0)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNone(SolicitudEmpresa.objects.get(empresa=empresa).recordatorio_enviado_en)
