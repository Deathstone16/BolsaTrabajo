"""Flujos de correo sin conexiones SMTP reales."""

import re
from urllib.parse import urlsplit

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Usuario


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='notificaciones@example.com',
    SECURE_SSL_REDIRECT=False,
)
class RecuperacionCorreoTests(TestCase):
    def test_recuperacion_envia_enlace_y_permite_cambiar_contrasena(self):
        usuario = Usuario.objects.create_user(
            email='postulante@example.com', password='Clave-anterior-123!'
        )

        respuesta = self.client.post(
            reverse('recuperar-contrasena'), {'email': usuario.email}
        )

        self.assertRedirects(respuesta, reverse('recuperacion-enviada'))
        self.assertEqual(len(mail.outbox), 1)
        mensaje = mail.outbox[0]
        self.assertEqual(mensaje.to, [usuario.email])
        self.assertEqual(mensaje.from_email, 'notificaciones@example.com')
        self.assertEqual(len(mensaje.alternatives), 1)
        enlace = re.search(r'http://testserver/usuarios/restablecer/\S+', mensaje.body)
        self.assertIsNotNone(enlace)
        html = mensaje.alternatives[0].content
        self.assertIn('href="' + enlace.group() + '"', html)
        self.assertIn('#F8F3F0', html)
        self.assertIn('#512DA8', html)
        self.assertIn('#FFDE59', html)
        self.assertIn('Bolsa de trabajo &middot; Chaco', html)
        self.assertNotIn('#2563eb', html)

        respuesta = self.client.post(urlsplit(enlace.group()).path, {
            'new_password1': 'Clave-nueva-segura-123!',
            'new_password2': 'Clave-nueva-segura-123!',
        })
        self.assertRedirects(respuesta, reverse('contrasena-restablecida'))
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('Clave-nueva-segura-123!'))

    def test_email_desconocido_muestra_la_misma_respuesta_sin_enviar(self):
        respuesta = self.client.post(
            reverse('recuperar-contrasena'), {'email': 'nadie@example.com'}
        )

        self.assertRedirects(respuesta, reverse('recuperacion-enviada'))
        self.assertEqual(len(mail.outbox), 0)
