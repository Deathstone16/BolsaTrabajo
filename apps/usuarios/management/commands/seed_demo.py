"""Datos sintéticos, repetibles y exclusivos del entorno local."""
from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from PIL import Image, ImageDraw
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from categorias.models import Categoria, Habilidad
from cursos.models import Curso
from ia.models import AnalisisCV, EventoSalida
from ia.workflow import publish_candidate_profile, publish_offer_profile
from matching.services import get_or_create_match
from usuarios.models import Usuario, Postulante, Oferente
from ofertas.models import Oferta
from ien_contracts.models import MatchResult


PASSWORD = 'DemoIEN2026!'


class Command(BaseCommand):
    help = 'Carga cuentas, cursos, ofertas y compatibilidades DEMO sin llamar a IA ni enviar correos.'

    def account(self, alias, first, last='', staff=False, admin=False):
        user, _ = Usuario.objects.get_or_create(email=f'{alias}@demo.example.test')
        user.first_name, user.last_name = first, last
        user.is_active, user.is_staff, user.is_superuser = True, staff, admin
        user.set_password(PASSWORD)
        user.save()
        return user

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Los datos demo solo se cargan con DEBUG=True.')
        now = timezone.now()
        categories = {name: Categoria.objects.get_or_create(nombre=name)[0]
                      for name in ['Tecnología', 'Marketing y comunicación', 'Administración', 'Atención al cliente']}
        self.account('admin', 'Administración', 'Demo', staff=True, admin=True)
        self.account('moderador', 'Moderación', 'Demo', staff=True)
        companies = []
        for index, (alias, name, industry, state) in enumerate([
            ('empresa', 'DEMO · Nube Sur', 'Tecnología', 'aprobado'),
            ('agencia', 'DEMO · Estudio Horizonte', 'Comunicación', 'aprobado'),
            ('empresa-pendiente', 'DEMO · Cooperativa Crecer', 'Servicios', 'pendiente'),
            ('empresa-rechazada', 'DEMO · Proyectos Delta', 'Comercio', 'rechazado'),
        ]):
            user = self.account(alias, name)
            Oferente.objects.update_or_create(usuario=user, defaults={
                'nombre_empresa': name, 'cuit': f'30-0000000{index}-0', 'industria': industry,
                'estado_validacion': state, 'tamano_empresa': '11-50', 'ubicacion': 'Córdoba, Argentina',
                'anio_fundacion': 2018 + index, 'sitio_web': 'https://example.test',
                'descripcion': 'Empresa ficticia para probar la bolsa de empleo. Todos los datos son de demostración.',
                'motivo_rechazo': 'DEMO: falta completar la documentación.' if state == 'rechazado' else '',
            })
            companies.append(user)

        candidates = []
        profiles = [
            ('postulante', 'Lucía', 'Demo', 'Backend developer', ['Python', 'Django', 'SQL', 'Git'], 'advanced'),
            ('marketing', 'Mateo', 'Demo', 'Marketing assistant', ['Content creation', 'Social media', 'Canva', 'Communication'], 'intermediate'),
            ('junior', 'Sofía', 'Demo', 'Junior administrative assistant', ['Excel', 'Customer service', 'Organization'], 'beginner'),
        ]
        for alias, first, last, headline, skills, level in profiles:
            user = self.account(alias, first, last)
            candidate, _ = Postulante.objects.get_or_create(usuario=user)
            content = {'profile_id': str(candidate.pk), 'headline': headline,
                       'summary': 'Synthetic demonstration profile for local testing.',
                       'skills': [{'name': name, 'level': level, 'evidence': ['DEMO: declared in a synthetic profile.']} for name in skills],
                       'work_experience': [{'job_title': headline, 'organization': 'DEMO company', 'duration_months': 24 if level == 'advanced' else 6}],
                       'education': [{'level': 'technical', 'field': 'Professional training', 'completed': True}],
                       'languages': [{'name': 'Spanish', 'level': 'native'}, {'name': 'English', 'level': 'basic'}],
                       'preferences': {'locations': ['Córdoba'], 'work_modes': ['remote', 'hybrid']}}
            analysis, _ = AnalisisCV.objects.get_or_create(postulante=candidate, error='DEMO', defaults={'estado': 'completado'})
            profile = publish_candidate_profile(candidate, content, '', 'demo', analysis)
            analysis.respuesta = {'status': 'completed', 'result': profile.contenido, 'demo': True}
            analysis.respondido_en = now
            analysis.save()
            candidates.append(candidate)

        definitions = [
            ('Desarrollador Python / Django', 'Tecnología', ['Python', 'Django', 'SQL'], 'remoto', 'activa', 0),
            ('Frontend React junior', 'Tecnología', ['JavaScript', 'React', 'CSS'], 'hibrido', 'activa', 0),
            ('Soporte técnico junior', 'Tecnología', ['Customer service', 'Windows', 'Networking'], 'presencial', 'activa', 0),
            ('Analista de datos', 'Tecnología', ['Python', 'SQL', 'Excel'], 'remoto', 'activa', 0),
            ('Community manager', 'Marketing y comunicación', ['Social media', 'Content creation', 'Canva'], 'hibrido', 'activa', 1),
            ('Asistente de marketing', 'Marketing y comunicación', ['Communication', 'Canva', 'Excel'], 'remoto', 'activa', 1),
            ('Auxiliar administrativo', 'Administración', ['Excel', 'Organization', 'Communication'], 'presencial', 'activa', 0),
            ('Atención al cliente', 'Atención al cliente', ['Customer service', 'Communication'], 'hibrido', 'activa', 1),
            ('Backend trainee sin experiencia', 'Tecnología', ['Python', 'Git'], 'remoto', 'activa', 0),
            ('Diseñador de contenidos', 'Marketing y comunicación', ['Canva', 'Content creation'], 'hibrido', 'pendiente', 1),
            ('Asistente comercial', 'Atención al cliente', ['Communication', 'Excel'], 'presencial', 'rechazada', 0),
            ('Administrativo contable', 'Administración', ['Excel', 'Organization'], 'presencial', 'finalizada', 0),
        ]
        offers = []
        for index, (title, category, skills, mode, state, company_index) in enumerate(definitions):
            offer, _ = Oferta.objects.update_or_create(empresa=companies[company_index], titulo=f'DEMO · {title}', defaults={
                'nombre_puesto': title, 'categoria': categories[category], 'ubicacion': 'Córdoba, Argentina',
                'modalidad': mode, 'estado': state, 'fecha_publicacion': now - timedelta(days=index),
                'fecha_cierre': now + timedelta(days=30) if state != 'finalizada' else now - timedelta(days=2),
                'experiencia_requerida': 'sin-experiencia' if 'junior' in title.lower() or 'trainee' in title.lower() else '1-2',
                'nivel_educativo': 'secundario', 'habilidades_duras': ', '.join(skills),
                'habilidades_blandas': 'Comunicación, Trabajo en equipo', 'habilidades_requeridas': ', '.join(skills),
                'descripcion': f'Oferta ficticia para pruebas: {title}.\nBuscamos una persona con conocimientos de {", ".join(skills)}.\nAcompañamiento del equipo, capacitación y oportunidades de crecimiento.\nTodos los datos de esta oferta son de demostración.',
                'motivo_rechazo': 'DEMO: falta detallar las responsabilidades.' if state == 'rechazada' else '',
            })
            for skill in skills:
                Habilidad.objects.get_or_create(nombre=skill, categoria=categories[category], defaults={'tipo_habilidad': 'D'})
            offer_content = {'offer_id': str(offer.pk), 'title': title, 'location': 'Córdoba',
                             'work_mode': {'remoto': 'remote', 'hibrido': 'hybrid', 'presencial': 'onsite'}[mode],
                             'requirements': [{'name': name, 'minimum_level': 'intermediate', 'mandatory': True} for name in skills]}
            publish_offer_profile(offer, offer_content, '')
            if state == 'activa':
                offers.append((offer, skills))

        for index, (title, category, duration, kind) in enumerate([
            ('Python desde cero', 'Tecnología', '8 semanas', 'Virtual'),
            ('Desarrollo web con React', 'Tecnología', '12 semanas', 'Hibrido'),
            ('Excel para el trabajo', 'Administración', '6 semanas', 'Virtual'),
            ('Marketing digital y redes', 'Marketing y comunicación', '8 semanas', 'Hibrido'),
            ('Comunicación y atención al cliente', 'Atención al cliente', '4 semanas', 'Presencial'),
            ('Preparación para entrevistas', 'Administración', '3 semanas', 'Virtual'),
        ]):
            course, _ = Curso.objects.update_or_create(nombre=f'DEMO · {title}', defaults={
                'categoria': categories[category], 'descripcion': f'Curso de demostración: {title}. Incluye ejercicios prácticos y acompañamiento docente. No es una inscripción real.',
                'duracion': duration, 'horario': 'Martes y jueves de 18:00 a 20:00', 'tipo': kind,
                'url_externa': 'https://example.test/cursos', 'activo': True,
            })
            if not course.imagen:
                picture = Image.new('RGB', (960, 540), ['#512DA8', '#235F70', '#A46322'][index % 3])
                draw = ImageDraw.Draw(picture)
                draw.rectangle((55, 55, 905, 485), outline='#F4D18A', width=5)
                draw.text((90, 200), f'IEN / DEMO\n\n{title}', fill='white', font_size=36)
                buffer = BytesIO()
                picture.save(buffer, format='PNG')
                course.imagen.save(f'demo-curso-{index}.png', ContentFile(buffer.getvalue()), save=True)

        with patch('matching.services._read_cache', return_value=None), patch('matching.services._allow_new_request', return_value=True):
            for candidate in candidates:
                known = {skill['name'].casefold() for skill in candidate.perfil_ia.contenido['skills']}
                for offer, skills in offers:
                    match, _ = get_or_create_match(candidate, offer)
                    assessments = [{'name': name, 'score': 1 if name.casefold() in known else 0,
                                    'status': 'met' if name.casefold() in known else 'unknown', 'mandatory': True,
                                    'explanation': 'Resultado ficticio de demostración.'} for name in skills]
                    ratio = sum(item['score'] for item in assessments) / len(assessments)
                    result = MatchResult(request_id=match.request_id, match_percentage=round(25 + ratio * 70),
                                         coverage_percentage=round(ratio * 100), confidence_percentage=80,
                                         assessments=assessments, summary='DEMO: porcentaje simulado, sin llamadas a proveedores.').model_dump(mode='json')
                    match.resultado, match.estado = result, 'completed'
                    match.match_percentage, match.coverage_percentage, match.confidence_percentage = result['match_percentage'], result['coverage_percentage'], 80
                    match.error = ''
                    match.save()
                    EventoSalida.objects.filter(tipo='match', payload__match_id=match.pk).update(estado='sent')
        self.stdout.write(self.style.SUCCESS('DEMO: 3 postulantes, 4 empresas, administrador, moderador, 12 ofertas, 6 cursos y 27 compatibilidades.'))
        self.stdout.write('Contraseña de las cuentas @demo.example.test: ' + PASSWORD)
        self.stdout.write('El proyecto aún no implementa postulaciones a ofertas; no se inventaron registros de ese modelo.')
