import asyncio
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone
from categorias.models import Categoria
from ofertas.models import Oferta
from .matching import comparar_oferta_con_analisis
import hashlib
import hmac
import json
import time

from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from usuarios.models import Postulante, Usuario

from .models import AnalisisCV, ComparacionOfertaCV, EventoSalida, PerfilCV, TrabajoExtraccion
from .workflow import publish_candidate_profile, request_cv_extraction, request_profile_normalization
from .consumers import CVAnalysisConsumer, TOKEN_SALT


@override_settings(
    IA_API_URL='http://api-externa.test/api/v1/cv-analyses',
    IA_API_TOKEN='token-de-servicio',
    IA_CALLBACK_TOKEN='token-de-callback',
    IA_CALLBACK_HMAC_SECRET='token-de-callback',
    CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}},
)
class AnalisisCVViewsTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(email='postulante@example.com', password='clave-segura')
        self.postulante = Postulante.objects.create(
            usuario=self.usuario,
            cv=SimpleUploadedFile('cv.pdf', b'%PDF-1.4 contenido'),
        )
        self.client.force_login(self.usuario)

    def _result(self):
        return {
            'schema_version': 'candidate-profile.v1',
            'profile_id': str(self.postulante.id),
            'headline': 'Backend developer',
            'summary': 'Python developer.',
            'skills': [{'name': 'Python', 'level': 'intermediate', 'evidence': ['Resume skills section']}],
            'work_experience': [], 'education': [], 'languages': [],
            'preferences': {'locations': [], 'work_modes': []},
        }

    def _callback(self, job, status='completed', result=None, error=None):
        payload = {
            'event_id': f'event-{job.pk}-{status}',
            'job_id': 'remote-job-1',
            'request_id': job.clave_idempotencia,
            'analysis_id': job.analisis_cv_id,
            'candidate_id': self.postulante.id,
            'offer_id': None,
            'kind': 'candidate_cv',
            'source_hash': job.source_hash,
            'status': status,
            'result': result,
            'error': error,
        }
        body = json.dumps(payload).encode('utf-8')
        timestamp = str(int(time.time()))
        signature = hmac.new(
            b'token-de-callback', timestamp.encode('ascii') + b'.' + body, hashlib.sha256
        ).hexdigest()
        return self.client.post(
            reverse('ia:llegue'), data=body, content_type='application/json',
            headers={'X-IA-Event-Timestamp': timestamp, 'X-IA-Callback-Signature': signature},
        )

    def test_crea_trabajo_y_outbox_sin_llamada_http(self):
        response = self.client.post(reverse('ia:solicitar_analisis'))
        self.assertEqual(response.status_code, 202)
        analysis = AnalisisCV.objects.get(postulante=self.postulante)
        job = TrabajoExtraccion.objects.get(analisis_cv=analysis)
        self.assertEqual(job.estado, TrabajoExtraccion.Estado.PENDIENTE)
        self.assertTrue(job.cv_snapshot.name)
        self.assertTrue(EventoSalida.objects.filter(payload__job_id=job.id).exists())

    def test_reutiliza_analisis_pendiente(self):
        analysis, job, _ = request_cv_extraction(self.postulante)
        response = self.client.post(reverse('ia:solicitar_analisis'))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()['analisis_id'], analysis.id)
        self.assertEqual(TrabajoExtraccion.objects.filter(analisis_cv=analysis).count(), 1)

    def test_nuevo_cv_se_habilita_cuando_anterior_termino(self):
        AnalisisCV.objects.create(postulante=self.postulante, estado=AnalisisCV.Estado.COMPLETADO)
        response = self.client.post(reverse('ia:solicitar_analisis'))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(AnalisisCV.objects.filter(postulante=self.postulante, estado=AnalisisCV.Estado.PENDIENTE).count(), 1)

    def test_base_de_datos_impide_dos_analisis_pendientes(self):
        AnalisisCV.objects.create(postulante=self.postulante)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AnalisisCV.objects.create(postulante=self.postulante)

    def test_callback_firmado_guarda_perfil_canonico(self):
        _, job, _ = request_cv_extraction(self.postulante)
        response = self._callback(job, result=self._result())
        self.assertEqual(response.status_code, 200)
        job.refresh_from_db()
        profile = PerfilCV.objects.get(postulante=self.postulante)
        self.assertEqual(job.estado, TrabajoExtraccion.Estado.COMPLETADO)
        self.assertEqual(profile.version, 1)
        self.assertEqual(profile.contenido['schema_version'], 'candidate-profile.v1')

    def test_callback_duplicado_es_idempotente(self):
        _, job, _ = request_cv_extraction(self.postulante)
        self.assertEqual(self._callback(job, result=self._result()).status_code, 200)
        duplicate = self._callback(job, result=self._result())
        self.assertEqual(duplicate.status_code, 200)
        self.assertTrue(duplicate.json()['duplicado'])
        self.assertEqual(PerfilCV.objects.get(postulante=self.postulante).version, 1)

    def test_callback_error_marca_analisis(self):
        analysis, job, _ = request_cv_extraction(self.postulante)
        response = self._callback(job, status='failed', error='PDF could not be read.')
        self.assertEqual(response.status_code, 200)
        analysis.refresh_from_db()
        self.assertEqual(analysis.estado, AnalisisCV.Estado.ERROR)

    def test_edicion_se_normaliza_antes_de_reemplazar_el_perfil_canonico(self):
        profile = publish_candidate_profile(
            self.postulante, self._result(), 'a' * 64, 'extraction'
        )
        edited = dict(profile.contenido)
        edited['summary'] = 'Desarrolladora Python con experiencia en APIs.'

        job, created = request_profile_normalization(self.postulante, edited, profile.version)

        self.assertTrue(created)
        profile.refresh_from_db()
        self.assertEqual(profile.estado, 'processing')
        self.assertEqual(job.tipo, TrabajoExtraccion.Tipo.NORMALIZAR_PERFIL)
        self.assertTrue(EventoSalida.objects.filter(payload__job_id=job.id).exists())

        normalized = self._result()
        normalized['summary'] = 'Python developer with API experience.'
        self.assertEqual(self._callback(job, result=normalized).status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.estado, 'ready')
        self.assertEqual(profile.origen, 'user_edit')
        self.assertEqual(profile.contenido['summary'], normalized['summary'])

    def test_cv_nuevo_reemplaza_perfil_editado_al_completar(self):
        profile = publish_candidate_profile(
            self.postulante, self._result(), 'a' * 64, 'extraction'
        )
        profile.origen = 'user_edit'
        profile.save(update_fields=['origen', 'actualizado_en'])

        _, job, _ = request_cv_extraction(self.postulante)
        replacement = self._result()
        replacement['summary'] = 'New resume profile from the latest CV.'
        response = self._callback(job, result=replacement)

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.origen, 'extraction')
        self.assertEqual(profile.contenido['summary'], replacement['summary'])


    def test_postulante_guarda_todas_las_habilidades_sin_perder_sugerencia_ia(self):
        analisis = AnalisisCV.objects.create(
            postulante=self.postulante,
            estado=AnalisisCV.Estado.COMPLETADO,
            respuesta={'result': {'habilidades_analizadas': [
                {'tecnologia': 'Python', 'nivel_evaluado': 'Principiante'},
                {'tecnologia': 'Django', 'nivel_evaluado': 'Intermedio'},
            ]}},
        )
        resultado_url = reverse('ia:ver_resultado', args=[analisis.id])
        editar_url = reverse('ia:editar_habilidades', args=[analisis.id])

        self.assertContains(self.client.get(resultado_url), editar_url)
        self.assertNotContains(self.client.get(resultado_url), 'name="nivel_0"')
        self.assertContains(self.client.get(editar_url), 'name="nivel_0"')
        response = self.client.post(
            editar_url,
            {'opinion_0': 'no', 'nivel_0': 'Avanzado', 'opinion_1': 'si', 'nivel_1': 'Intermedio'},
        )

        self.assertRedirects(response, resultado_url)
        analisis.refresh_from_db()
        primera, segunda = analisis.respuesta['result']['habilidades_analizadas']
        self.assertEqual(primera['nivel_evaluado'], 'Principiante')
        self.assertEqual(primera['nivel_usuario'], 'Avanzado')
        self.assertEqual(primera['acuerdo_usuario'], 'no')
        self.assertEqual(segunda['nivel_usuario'], 'Intermedio')
        self.assertEqual(segunda['acuerdo_usuario'], 'si')

    def test_no_se_puede_editar_analisis_ajeno_ni_nivel_invalido(self):
        otro_usuario = Usuario.objects.create_user(email='otro@example.com', password='clave-segura')
        otro_postulante = Postulante.objects.create(usuario=otro_usuario)
        analisis = AnalisisCV.objects.create(
            postulante=otro_postulante,
            estado=AnalisisCV.Estado.COMPLETADO,
            respuesta={'result': {'habilidades_analizadas': [
                {'tecnologia': 'Python', 'nivel_evaluado': 'Principiante'},
            ]}},
        )
        url = reverse('ia:editar_habilidades', args=[analisis.id])

        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(otro_usuario)
        self.assertEqual(self.client.post(url, {'opinion_0': 'si', 'nivel_0': 'Experto'}).status_code, 400)

    def test_nivel_invalido_no_guarda_ninguna_habilidad(self):
        analisis = AnalisisCV.objects.create(
            postulante=self.postulante,
            estado=AnalisisCV.Estado.COMPLETADO,
            respuesta={'result': {'habilidades_analizadas': [
                {'tecnologia': 'Python', 'nivel_evaluado': 'Principiante'},
                {'tecnologia': 'Django', 'nivel_evaluado': 'Intermedio'},
            ]}},
        )

        response = self.client.post(
            reverse('ia:editar_habilidades', args=[analisis.id]),
            {'opinion_0': 'no', 'nivel_0': 'Avanzado', 'opinion_1': 'si', 'nivel_1': 'Experto'},
        )

        self.assertEqual(response.status_code, 400)
        analisis.refresh_from_db()
        self.assertNotIn('nivel_usuario', analisis.respuesta['result']['habilidades_analizadas'][0])

@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class CVAnalysisConsumerTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(email='ws@example.com', password='clave-segura')

    def test_consumer_recibe_broadcast_solo_con_token_del_usuario(self):
        async def scenario():
            token = signing.dumps(self.usuario.pk, salt=TOKEN_SALT)
            socket = WebsocketCommunicator(CVAnalysisConsumer.as_asgi(), f'/ws/cv-analysis/?token={token}')
            socket.scope['user'] = self.usuario
            connected, _ = await socket.connect()
            self.assertTrue(connected)
            await get_channel_layer().group_send(f'user_{self.usuario.pk}', {
                'type': 'cv.analysis.complete',
                'payload': {'analysis_id': 42, 'status': 'completado'},
            })
            self.assertEqual(await socket.receive_json_from(), {
                'type': 'cv.analyzed',
                'payload': {'analysis_id': 42, 'status': 'completado'},
            })
            await socket.disconnect()

            bad = WebsocketCommunicator(CVAnalysisConsumer.as_asgi(), '/ws/cv-analysis/?token=invalid')
            bad.scope['user'] = self.usuario
            connected, _ = await bad.connect()
            self.assertFalse(connected)

        asyncio.run(scenario())


class ComparacionOfertaCVTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            email='match@example.com',
            password='clave-segura',
        )
        self.postulante = Postulante.objects.create(usuario=self.usuario)
        self.empresa = Usuario.objects.create_user(
            email='empresa-match@example.com',
            password='clave-segura',
        )
        self.categoria = Categoria.objects.create(nombre='Tecnología')
        self.oferta = Oferta.objects.create(
            empresa=self.empresa,
            categoria=self.categoria,
            titulo='Desarrollador backend',
            nombre_puesto='Backend Developer',
            ubicacion='Resistencia',
            descripcion='Desarrollo de aplicaciones.',
            habilidades_duras='Python, Django, SQL',
            habilidades_blandas='Comunicación',
            habilidades_requeridas='Python, Django, SQL, Comunicación',
            nivel_educativo='universitario',
            estado='activa',
            fecha_cierre=timezone.now() + timedelta(days=10),
        )
        self.analisis = AnalisisCV.objects.create(
            postulante=self.postulante,
            estado=AnalisisCV.Estado.COMPLETADO,
            respuesta={
                'status': 'completed',
                'result': {
                    'habilidades_analizadas': [
                        {'tecnologia': 'Python', 'nivel_evaluado': 'Intermedio'},
                        {'tecnologia': 'Django REST Framework', 'nivel_evaluado': 'Principiante'},
                    ],
                },
            },
        )

    def test_calcula_porcentaje_con_datos_guardados_del_cv(self):
        resultado = comparar_oferta_con_analisis(self.oferta, self.analisis)

        self.assertEqual(resultado['porcentaje'], 50)
        self.assertEqual(
            [item['requisito'] for item in resultado['coincidencias']],
            ['Python', 'Django'],
        )
        self.assertEqual(resultado['habilidades_faltantes'], ['SQL', 'Comunicación'])

    @patch('ia.management.commands.dispatch_integration_outbox.requests.post')
    def test_comparar_oferta_no_vuelve_a_llamar_al_analizador_de_cv(self, post):
        self.client.force_login(self.usuario)

        response = self.client.post(reverse('comparar_oferta_cv', args=[self.oferta.pk]))

        self.assertRedirects(response, reverse('detalle_oferta', args=[self.oferta.pk]))
        comparacion = ComparacionOfertaCV.objects.get(
            postulante=self.postulante,
            oferta=self.oferta,
            analisis=self.analisis,
        )
        self.assertEqual(comparacion.porcentaje, 50)
        post.assert_not_called()

    def test_detalle_no_calcula_match_automaticamente(self):
        self.client.force_login(self.usuario)

        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Comparar con mi CV')
        self.assertFalse(ComparacionOfertaCV.objects.exists())

    def test_repetir_comparacion_actualiza_el_resultado_guardado(self):
        self.client.force_login(self.usuario)
        url = reverse('comparar_oferta_cv', args=[self.oferta.pk])

        self.client.post(url)
        self.oferta.habilidades_requeridas = 'Python'
        self.oferta.save(update_fields=['habilidades_requeridas'])
        self.client.post(url)

        self.assertEqual(ComparacionOfertaCV.objects.count(), 1)
        self.assertEqual(ComparacionOfertaCV.objects.get().porcentaje, 100)

    def test_no_usa_analisis_de_un_cv_anterior(self):
        self.postulante.cv_fecha_carga = timezone.now() + timedelta(seconds=1)
        self.postulante.save(update_fields=['cv_fecha_carga'])
        self.client.force_login(self.usuario)

        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))

        self.assertIsNone(response.context['analisis_cv'])
        self.assertContains(response, 'Primero necesitás analizar tu CV')

    def test_no_muestra_comparacion_si_cambiaron_los_requisitos(self):
        self.client.force_login(self.usuario)
        url = reverse('comparar_oferta_cv', args=[self.oferta.pk])
        self.client.post(url)
        self.oferta.habilidades_requeridas = 'Python, Docker'
        self.oferta.save(update_fields=['habilidades_requeridas'])

        response = self.client.get(reverse('detalle_oferta', args=[self.oferta.pk]))

        self.assertIsNone(response.context['comparacion'])
        self.assertContains(response, 'Comparar con mi CV')
