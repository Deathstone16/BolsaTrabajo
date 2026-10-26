"""Pruebas de integración para los flujos afectados por la integración de ramas."""

import tempfile
from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from cursos.models import Curso
from ia.models import AnalisisCV, CVVersion, PerfilCV, PerfilOferta
from matching.configuration import scoring_hash
from matching.models import ConfiguracionActiva, ConfiguracionCompatibilidad
from ofertas.models import Oferta

from .models import Oferente, Postulante, Usuario


class FlujosIntegracionRamasTests(TestCase):
    """Verifica comportamientos de usuario que cruzan los cambios integrados."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_dir = tempfile.TemporaryDirectory(prefix='ien-integracion-media-')
        cls.settings_override = override_settings(MEDIA_ROOT=cls.media_dir.name)
        cls.settings_override.enable()
        cls.addClassCleanup(cls.settings_override.disable)
        cls.addClassCleanup(cls.media_dir.cleanup)

    def crear_postulante(self, email='postulante@example.com'):
        usuario = Usuario.objects.create_user(email=email, password='Clave-segura-123!')
        postulante = Postulante.objects.create(usuario=usuario)
        return usuario, postulante

    def test_registro_oferente_valido_informa_revision_pendiente(self):
        response = self.client.post(
            reverse('registro') + '?tipo=oferente',
            {
                'nombre_empresa': 'Empresa de prueba',
                'cuit': '20-12345678-6',
                'email': 'empresa-integracion@example.com',
                'password1': 'Clave-segura-123!',
                'password2': 'Clave-segura-123!',
            },
        )

        self.assertRedirects(response, reverse('registro_exitoso') + '?tipo=oferente')
        success = self.client.get(response['Location'])
        empresa = Oferente.objects.get(usuario__email='empresa-integracion@example.com')
        self.assertEqual(empresa.cuit, '20-12345678-6')
        self.assertEqual(empresa.estado_validacion, Oferente.EstadoValidacion.PENDIENTE)
        self.assertContains(success, 'Tu empresa quedó en revisión')
        self.assertContains(success, 'pendiente de validación')

    def test_cursos_publicos_solo_exponen_cursos_activos(self):
        categoria = Categoria.objects.create(nombre='Formación integración')
        activo = Curso.objects.create(
            nombre='Curso activo de prueba', categoria=categoria, imagen='cursos/activo.png',
            descripcion='Contenido público', duracion='8 horas', horario='A convenir', activo=True,
        )
        inactivo = Curso.objects.create(
            nombre='Curso inactivo de prueba', categoria=categoria, imagen='cursos/inactivo.png',
            descripcion='Contenido retirado', duracion='8 horas', horario='A convenir', activo=False,
        )

        listado = self.client.get(reverse('cursos:listado'))
        detalle_activo = self.client.get(reverse('cursos:detalle', args=[activo.pk]))
        detalle_inactivo = self.client.get(reverse('cursos:detalle', args=[inactivo.pk]))

        self.assertContains(listado, activo.nombre)
        self.assertNotContains(listado, inactivo.nombre)
        self.assertContains(detalle_activo, activo.nombre)
        self.assertEqual(detalle_inactivo.status_code, 404)

    def test_perfil_postulante_conserva_controles_cv_y_scripts_de_interaccion(self):
        usuario, _ = self.crear_postulante()
        self.client.force_login(usuario)

        response = self.client.get(reverse('mi_perfil'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="form-cv-upload"')
        self.assertContains(response, 'id="cv-upload-area"')
        self.assertContains(response, 'js/cv_upload.js')
        self.assertContains(response, 'id="perfil-siguiente-paso"', count=1)
        self.assertContains(response, 'Empezá por cargar tu CV')

    def test_analisis_pendiente_tiene_indicador_global_solo_para_su_propietario(self):
        usuario, postulante = self.crear_postulante()
        version = CVVersion.objects.create(
            postulante=postulante, numero=1, archivo='cv-sintetico.pdf',
            nombre_original='cv.pdf', sha256='a' * 64, formato='pdf', tamano=10,
        )
        postulante.cv_version_actual = version
        postulante.save(update_fields=['cv_version_actual'])
        analysis = AnalisisCV.objects.create(postulante=postulante, version_cv=version)
        self.client.force_login(usuario)
        for url in (reverse('home'), reverse('buscar_empleo'), reverse('mi_perfil')):
            response = self.client.get(url)
            self.assertEqual(response.context['cv_pending_analysis_id'], analysis.pk)
            self.assertContains(response, 'id="cv-analysis-global"')
            self.assertContains(response, 'Podés seguir navegando. Te avisaremos cuando esté listo.')
            self.assertContains(response, f'data-user-id="{usuario.pk}"')
        other, _ = self.crear_postulante('otro-progreso@example.com')
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('home')).context['cv_pending_analysis_id'], '')

    def test_perfil_con_cv_muestra_una_sola_tarjeta_sin_pedir_cargarlo_otra_vez(self):
        usuario, postulante = self.crear_postulante()
        version = CVVersion.objects.create(
            postulante=postulante, numero=1, archivo='fixture-cv.pdf',
            nombre_original='CV de prueba.pdf', sha256='a' * 64,
            formato='pdf', tamano=123,
        )
        postulante.cv_version_actual = version
        postulante.save(update_fields=['cv_version_actual'])
        self.client.force_login(usuario)

        response = self.client.get(reverse('mi_perfil'))

        self.assertContains(response, 'id="perfil-siguiente-paso"', count=1)
        self.assertContains(response, 'CV de prueba.pdf')
        self.assertContains(response, 'id="form-analizar-cv"')
        self.assertContains(response, 'id="form-cv-upload"')
        self.assertNotContains(response, 'Empezá por cargar tu CV')

    def test_descarga_cv_no_filtra_archivos_a_anonimos_ni_a_otro_postulante(self):
        _, propietario = self.crear_postulante()
        otro_usuario, _ = self.crear_postulante('otro@example.com')
        version = CVVersion.objects.create(
            postulante=propietario,
            numero=1,
            archivo='fixture-no-escribe-archivo.pdf',
            nombre_original='confidencial.pdf',
            sha256='a' * 64,
            formato='pdf',
            tamano=123,
        )
        url = reverse('descargar_cv', args=[version.pk])

        anonimo = self.client.get(url)
        self.client.force_login(otro_usuario)
        otro_postulante = self.client.get(url)
        media_directa = self.client.get('/media/postulantes/cv/confidencial.pdf')

        self.assertEqual(anonimo.status_code, 302)
        self.assertEqual(otro_postulante.status_code, 404)
        self.assertEqual(media_directa.status_code, 404)

    def test_detalle_de_oferta_muestra_match_v2_y_hash_activo_al_postulante(self):
        usuario, postulante = self.crear_postulante()
        version = CVVersion.objects.create(
            postulante=postulante,
            numero=1,
            archivo='fixture-no-escribe-archivo.pdf',
            nombre_original='perfil.pdf',
            sha256='b' * 64,
            formato='pdf',
            tamano=456,
        )
        postulante.cv_version_actual = version
        postulante.save(update_fields=['cv_version_actual'])
        PerfilCV.objects.create(
            postulante=postulante,
            cv_version=version,
            version=1,
            source_hash='c' * 64,
            estado='ready',
            contenido={'skills': [{'name': 'Python'}]},
        )
        categoria = Categoria.objects.create(nombre='Tecnología integración')
        oferta = Oferta.objects.create(
            empresa=Usuario.objects.create_user(email='empresa-oferta@example.com', password='pass'),
            categoria=categoria,
            titulo='Desarrollador de integración',
            nombre_puesto='Backend',
            ubicacion='Remoto',
            descripcion='Construir servicios.',
            habilidades_requeridas='Python',
            habilidades_duras='Python',
            requisitos_obligatorios='Python avanzado',
            requisitos_deseables='Experiencia con colas',
            requisitos_estructurados=[
                {'id': 'python', 'category': 'technical_skills', 'source': 'requisitos_obligatorios',
                 'name': 'Python avanzado', 'mandatory': True, 'exclusionary': False},
                {'id': 'queues', 'category': 'desirables', 'source': 'requisitos_deseables',
                 'name': 'Experiencia con colas', 'mandatory': False, 'exclusionary': False},
            ],
            requiere_revision_requisitos=False,
            nivel_educativo='universitario',
            estado='activa',
            fecha_cierre=timezone.localdate() + timedelta(days=7),
        )
        PerfilOferta.objects.create(
            oferta=oferta,
            version=1,
            source_hash='d' * 64,
            estado='ready',
            contenido={'requirements': oferta.requisitos_estructurados},
        )
        configuracion, _ = ConfiguracionCompatibilidad.objects.get_or_create(
            version='test-integracion-v2',
            defaults={'es_borrador': False},
        )
        ConfiguracionActiva.objects.update_or_create(
            singleton='actual', defaults={'configuracion': configuracion},
        )
        self.client.force_login(usuario)

        response = self.client.get(reverse('detalle_oferta', args=[oferta.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-config-hash="{scoring_hash(configuracion)}"')
        self.assertContains(response, 'id="match-card"')
        self.assertTrue(response.context['oferta'].requisitos_estructurados[0]['mandatory'])
        self.assertContains(response, 'requisitos obligatorios')
        self.assertNotContains(response, '<<<<<<<')
