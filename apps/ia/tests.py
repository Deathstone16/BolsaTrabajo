from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.models import Postulante, Usuario

from .models import AnalisisCV


@override_settings(
    IA_API_URL='http://api-externa.test/analizar',
    IA_API_TOKEN='token-de-servicio',
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
    def test_envia_pdf_y_crea_solicitud(self, post):
        respuesta_api = Mock()
        respuesta_api.raise_for_status.return_value = None
        post.return_value = respuesta_api

        response = self.client.post(reverse('ia:solicitar_analisis'))

        self.assertEqual(response.status_code, 202)
        analisis = AnalisisCV.objects.get(postulante=self.postulante)
        data = post.call_args.kwargs['data']
        files = post.call_args.kwargs['files']
        self.assertEqual(data['analysis_id'], analisis.id)
        self.assertEqual(data['candidate_id'], self.postulante.id)
        self.assertTrue(files['cv'][0].endswith('.pdf'))
        self.assertEqual(files['cv'][2], 'application/pdf')
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Bearer token-de-servicio')

    @patch('ia.views.requests.post')
    def test_reutiliza_solicitud_pendiente_sin_llamar_nuevamente_a_la_api(self, post):
        pendiente = AnalisisCV.objects.create(postulante=self.postulante)

        response = self.client.post(reverse('ia:solicitar_analisis'))

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()['analisis_id'], pendiente.id)
        self.assertEqual(AnalisisCV.objects.filter(postulante=self.postulante).count(), 1)
        post.assert_not_called()

    @patch('ia.views.requests.post')
    def test_permite_nuevo_analisis_cuando_el_anterior_termino(self, post):
        AnalisisCV.objects.create(
            postulante=self.postulante,
            estado=AnalisisCV.Estado.COMPLETADO,
        )
        respuesta_api = Mock()
        respuesta_api.raise_for_status.return_value = None
        post.return_value = respuesta_api

        response = self.client.post(reverse('ia:solicitar_analisis'))

        self.assertEqual(response.status_code, 202)
        self.assertEqual(AnalisisCV.objects.filter(postulante=self.postulante).count(), 2)
        self.assertEqual(
            AnalisisCV.objects.filter(
                postulante=self.postulante,
                estado=AnalisisCV.Estado.PENDIENTE,
            ).count(),
            1,
        )
        post.assert_called_once()

    def test_base_de_datos_impide_dos_analisis_pendientes(self):
        AnalisisCV.objects.create(postulante=self.postulante)

        with self.assertRaises(IntegrityError), transaction.atomic():
            AnalisisCV.objects.create(postulante=self.postulante)

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
