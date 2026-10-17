"""Ofertas ficticias, pero verosímiles, para revisar páginas públicas en local."""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from categorias.models import Categoria
from ofertas.models import Oferta
from usuarios.models import Oferente, Usuario


DEMO_COMPANIES = (
    {
        'email': 'litoral-soluciones@seo-demo.invalid',
        'nombre_empresa': 'Litoral Soluciones (demo)',
        'cuit': '30-00000000-7',
        'industria': 'Servicios tecnológicos',
        'ubicacion': 'Resistencia, Chaco',
        'descripcion': 'Empresa ficticia creada para probar el buscador y el detalle de ofertas.',
    },
    {
        'email': 'rio-norte-gestion@seo-demo.invalid',
        'nombre_empresa': 'Río Norte Gestión (demo)',
        'cuit': '30-00000001-5',
        'industria': 'Servicios empresariales',
        'ubicacion': 'Corrientes, Corrientes',
        'descripcion': 'Empresa ficticia creada para probar el buscador y el detalle de ofertas.',
    },
)

DEMO_OFFERS = (
    {
        'company': 'litoral-soluciones@seo-demo.invalid',
        'categoria': 'Tecnología',
        'titulo': 'Analista de datos junior',
        'nombre_puesto': 'Analista de datos',
        'ubicacion': 'Resistencia, Chaco',
        'modalidad': 'hibrido',
        'experiencia_requerida': '1-2',
        'nivel_educativo': 'terciario',
        'habilidades_duras': 'Excel, SQL, Power BI',
        'habilidades_blandas': 'Comunicación, Atención al detalle',
        'descripcion': (
            'Buscamos una persona para transformar datos operativos en reportes claros para los equipos de ventas y atención. '
            'Vas a limpiar bases de datos, construir tableros en Power BI y presentar hallazgos en reuniones semanales.\n\n'
            'Se valoran estudios en análisis de datos, informática o carreras afines, manejo de Excel y SQL, y al menos un año '
            'de experiencia con reportes. Modalidad híbrida en Resistencia.\n\n'
            'Aviso ficticio de demostración: no recibe postulaciones reales.'
        ),
    },
    {
        'company': 'litoral-soluciones@seo-demo.invalid',
        'categoria': 'Tecnología',
        'titulo': 'Técnico/a de soporte informático',
        'nombre_puesto': 'Soporte técnico',
        'ubicacion': 'Resistencia, Chaco',
        'modalidad': 'presencial',
        'experiencia_requerida': 'menos-1',
        'nivel_educativo': 'terciario',
        'habilidades_duras': 'Windows, Redes, Hardware',
        'habilidades_blandas': 'Paciencia, Resolución de problemas',
        'descripcion': (
            'Sumate al equipo que acompaña a usuarios internos en la instalación de equipos, configuración de cuentas '
            'y resolución de incidentes de conectividad. La posición incluye registro de tickets y seguimiento hasta su cierre.\n\n'
            'Se requiere conocimiento básico de redes y mantenimiento de PC, buena comunicación y disponibilidad '
            'para trabajar de forma presencial en Resistencia.\n\n'
            'Aviso ficticio de demostración: no recibe postulaciones reales.'
        ),
    },
    {
        'company': 'rio-norte-gestion@seo-demo.invalid',
        'categoria': 'Administración',
        'titulo': 'Asistente administrativo/a',
        'nombre_puesto': 'Administración general',
        'ubicacion': 'Corrientes, Corrientes',
        'modalidad': 'presencial',
        'experiencia_requerida': '1-2',
        'nivel_educativo': 'secundario',
        'habilidades_duras': 'Excel, Facturación, Gestión documental',
        'habilidades_blandas': 'Organización, Trabajo en equipo',
        'descripcion': (
            'La persona seleccionada organizará documentación comercial, cargará comprobantes y dará seguimiento '
            'a consultas de proveedores. Trabajará junto al área contable para mantener registros actualizados.\n\n'
            'Se busca experiencia previa en tareas administrativas, dominio de planillas de cálculo y atención al detalle. '
            'Jornada presencial de lunes a viernes en Corrientes capital.\n\n'
            'Aviso ficticio de demostración: no recibe postulaciones reales.'
        ),
    },
    {
        'company': 'rio-norte-gestion@seo-demo.invalid',
        'categoria': 'Atención al cliente',
        'titulo': 'Representante de atención al cliente',
        'nombre_puesto': 'Atención al cliente',
        'ubicacion': 'Argentina (remoto)',
        'modalidad': 'remoto',
        'experiencia_requerida': 'sin-experiencia',
        'nivel_educativo': 'secundario',
        'habilidades_duras': 'Correo electrónico, CRM',
        'habilidades_blandas': 'Empatía, Comunicación',
        'descripcion': (
            'Atenderás consultas por correo y chat, registrarás cada caso en el CRM y derivarás situaciones '
            'que requieran intervención de otros equipos. El puesto ofrece capacitación inicial y trabajo remoto.\n\n'
            'Se valoran redacción clara, trato cordial y manejo básico de herramientas digitales. '
            'No se exige experiencia previa.\n\n'
            'Aviso ficticio de demostración: no recibe postulaciones reales.'
        ),
    },
)


class Command(BaseCommand):
    help = 'Carga ofertas ficticias para revisar SEO en desarrollo; no duplica registros al repetirlo.'

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Este comando sólo se puede ejecutar con DEBUG=True; nunca publica demos en producción.')

        companies = {}
        for data in DEMO_COMPANIES:
            email = data['email']
            user = Usuario.objects.filter(email=email).first()
            if user is None:
                user = Usuario(email=email, is_active=False)
                user.set_unusable_password()
                user.save()
            elif user.is_active or user.has_usable_password():
                raise CommandError(f'La cuenta {email} existe y no es una cuenta demo segura.')

            profile, _ = Oferente.objects.get_or_create(
                usuario=user,
                defaults={
                    'estado_validacion': Oferente.EstadoValidacion.APROBADO,
                    'nombre_empresa': data['nombre_empresa'],
                    'cuit': data['cuit'],
                    'industria': data['industria'],
                    'ubicacion': data['ubicacion'],
                    'descripcion': data['descripcion'],
                },
            )
            if profile.nombre_empresa != data['nombre_empresa']:
                raise CommandError(f'La cuenta {email} ya pertenece a otra empresa.')
            companies[email] = user

        created_count = 0
        for data in DEMO_OFFERS:
            category, _ = Categoria.objects.get_or_create(nombre=data['categoria'])
            defaults = {key: value for key, value in data.items() if key not in {'company', 'categoria', 'titulo'}}
            defaults.update({
                'categoria': category,
                'habilidades_requeridas': ', '.join((data['habilidades_duras'], data['habilidades_blandas'])),
                'estado': 'activa',
                'fecha_cierre': timezone.now() + timedelta(days=60),
            })
            _, created = Oferta.objects.get_or_create(
                empresa=companies[data['company']],
                titulo=data['titulo'],
                defaults=defaults,
            )
            created_count += created

        self.stdout.write(self.style.SUCCESS(
            f'Ofertas demo creadas: {created_count}. Total de este conjunto: {len(DEMO_OFFERS)}.'
        ))
