from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.models import Postulante, Usuario

from .models import AnalisisCV


@override_settings(
    IA_API_URL='http://api-externa.test/analizar',
    IA_CALLBACK_TOKEN='token-de-callback',
)
class AnalisisCVViewsTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email='postulante@example.com',
            password='clave-segura',
        )
        self.postulante = Postulante.objects.create(
            usuario=self.usuario,
            cv=SimpleUploadedFile('cv.pdf', b'%PDF-1.4 contenido'),
        )
        self.client.force_login(self.usuario)

    @patch('ia.views.requests.post')
    @patch('ia.views.extraer_texto_cv', return_value='Experiencia con Python y Django')
    def test_envia_texto_y_crea_solicitud(self, extraer_texto, post):
        respuesta_api = Mock()
        respuesta_api.raise_for_status.return_value = None
        post.return_value = respuesta_api

        response = self.client.post(reverse('ia:solicitar_analisis'))

        self.assertEqual(response.status_code, 202)
        analisis = AnalisisCV.objects.get(postulante=self.postulante)
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['analysis_id'], analisis.id)
        self.assertEqual(payload['candidate_id'], self.postulante.id)
        self.assertEqual(payload['cv_text'], 'Experiencia con Python y Django')

    def test_callback_guarda_json_de_api_externa(self):
        analisis = AnalisisCV.objects.create(postulante=self.postulante)
        respuesta_externa = {
            'analysis_id': analisis.id,
            'candidate_id': self.postulante.id,
            'status': 'completed',
            'result': {'habilidades': ['Python', 'Django']},
            'error': None,
        }

        response = self.client.post(
            reverse('ia:llegue'),
            data=respuesta_externa,
            content_type='application/json',
            headers={'X-IA-Callback-Token': 'token-de-callback'},
        )

        self.assertEqual(response.status_code, 200)
        analisis.refresh_from_db()
        self.assertEqual(analisis.estado, AnalisisCV.Estado.COMPLETADO)
        self.assertEqual(analisis.respuesta, respuesta_externa)

    def test_callback_con_error_marca_el_analisis_como_error(self):
        analisis = AnalisisCV.objects.create(postulante=self.postulante)

        response = self.client.post(
            reverse('ia:llegue'),
            data={
                'analysis_id': analisis.id,
                'candidate_id': self.postulante.id,
                'status': 'failed',
                'result': None,
                'error': 'No se pudo procesar el CV.',
            },
            content_type='application/json',
            headers={'X-IA-Callback-Token': 'token-de-callback'},
        )

        self.assertEqual(response.status_code, 200)
        analisis.refresh_from_db()
        self.assertEqual(analisis.estado, AnalisisCV.Estado.ERROR)
        self.assertEqual(analisis.error, 'No se pudo procesar el CV.')
