"""Only synthetic data. No database records or CV uploads are read."""
from datetime import datetime, date, timezone
from types import SimpleNamespace as NS
from uuid import UUID

from categorias.models import Categoria
from cursos.models import Curso
from ofertas.models import Oferta
from usuarios.models import Usuario, Postulante, Oferente

DATE = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)
MATCH_ID = UUID('11111111-1111-4111-8111-111111111111')
SUMMARY = 'Analista de datos con experiencia en reportes comerciales y automatización de tareas. Maneja Python, Excel y SQL. Se destaca por comunicar resultados de forma clara y trabajar con equipos de distintas áreas.'


def fixtures():
    user = Usuario(pk=0, email='lucia.demo@example.com', first_name='Lucía', last_name='Gómez')
    user._state.fields_cache['oferente'] = None
    candidate = Postulante(pk=0, usuario=user, dni='40123456', fecha_nacimiento=date(1997, 5, 12), telefono='3624000000', direccion='Resistencia, Chaco')
    version = NS(pk=0, numero=1, formato='pdf', nombre_original='CV_Lucia_Gomez_DEMO.pdf', creado_en=DATE)
    candidate.cv_version_actual_id = 0
    company_user = Usuario(pk=1, email='empresa.demo@example.com')
    company = Oferente(pk=0, usuario=company_user, nombre_empresa='Norte Digital', cuit='30712345671', estado_validacion='aprobado', contacto_nombre='Alex Pérez', contacto_cargo='Recursos Humanos', correo_publico='rrhh@example.com', telefono='362 400 0000', ubicacion='Resistencia, Chaco', industria='Tecnología', tamano_empresa='11-50', descripcion='Empresa ficticia de tecnología y servicios digitales para la revisión de diseño.')
    category = Categoria(pk=0, nombre='Tecnología')
    offers = [Oferta(pk=i, empresa=company_user, categoria=category, titulo=title, nombre_puesto=title, ubicacion=location, modalidad=mode, estado='activa', descripcion='Sumate a un equipo que transforma información en decisiones. Vas a preparar reportes, automatizar tareas y colaborar en proyectos con impacto en la región.', requisitos_obligatorios='Python\nExcel', requisitos_deseables='SQL\nComunicación', habilidades_duras='Python, Excel, SQL', habilidades_blandas='Comunicación, Trabajo en equipo', experiencia_requerida='1-2', nivel_educativo='terciario', fecha_publicacion=DATE, fecha_cierre=datetime(2026, 12, 30, tzinfo=timezone.utc), requiere_revision_requisitos=False) for i, title, location, mode in [(0, 'Analista de datos', 'Resistencia, Chaco', 'hibrido'), (1, 'Asistente de administración', 'Corrientes, Corrientes', 'presencial'), (2, 'Desarrollador Python', 'Argentina', 'remoto')]]
    courses = [Curso(pk=i, nombre=name, categoria=category, descripcion='Curso ficticio para revisar el catálogo y los detalles. Aprendé con ejercicios prácticos y acompañamiento docente.', duracion=duration, horario='Martes y jueves de 18 a 20', tipo='Virtual', activo=True) for i, name, duration in [(0, 'Excel para el trabajo', '8 semanas'), (1, 'Python desde cero', '12 semanas'), (2, 'Comunicación en equipos', '4 semanas'), (3, 'SQL para análisis de datos', '8 semanas')]]
    skills = [
        {'name': 'Python', 'level': 'intermediate', 'kind': 'technical', 'evidence': ['Automatización de reportes y limpieza de datos con pandas.']},
        {'name': 'Excel', 'level': 'advanced', 'kind': 'technical', 'evidence': ['Tablas dinámicas, fórmulas y tableros comerciales.']},
        {'name': 'SQL', 'level': 'beginner', 'kind': 'technical', 'evidence': ['Consultas para extraer información de ventas.']},
        {'name': 'Comunicación', 'level': 'intermediate', 'kind': 'soft', 'evidence': ['Presentación semanal de resultados al equipo comercial.']},
        {'name': 'Trabajo en equipo', 'level': 'intermediate', 'kind': 'soft', 'evidence': ['Colaboración con administración y ventas.']},
    ]
    content = {
        'headline': 'Analista de datos', 'summary': SUMMARY, 'skills': skills,
        'work_experience': [{'job_title': 'Analista de reportes', 'organization': 'Comercial del Norte (ficticia)', 'duration_months': 24, 'highlights': ['Automaticé reportes de ventas con Python.', 'Diseñé tableros de seguimiento en Excel.']}],
        'education': [{'level': 'technical', 'field': 'Análisis de Sistemas', 'institution': 'Instituto de formación (ficticio)', 'completion_status': 'completed'}],
        'projects': [{'name': 'Tablero comercial', 'highlights': ['Visualización de ventas y objetivos mensuales.', 'Limpieza de datos y actualización automática de reportes.']}],
        'languages': [{'name': 'Español', 'level': 'native'}, {'name': 'Inglés', 'level': 'conversational'}],
        'credentials': [{'name': 'Excel avanzado', 'issuer': 'Centro de capacitación (ficticio)'}],
        'preferences': {'locations': ['Resistencia', 'Corrientes'], 'work_modes': ['hybrid', 'remote']},
    }
    profile = NS(estado='ready', contenido=content, version=1, actualizado_en=DATE, schema_version='candidate-profile.v2')
    evaluated = [{'tecnologia': skill['name'], 'nivel_evaluado': 'Intermedio', 'nivel_usuario': 'Intermedio', 'justificacion_evidencia': skill['evidence'][0]} for skill in skills[:3]]
    analysis = NS(pk=0, id=0, postulante=candidate, estado='completado', respondido_en=DATE, respuesta={'result': {'habilidades_analizadas': evaluated}}, perfil_snapshot=content)
    match = NS(request_id=MATCH_ID, oferta=offers[0], oferta_id=0, estado='completed', match_percentage=82, coverage_percentage=92, confidence_percentage=90, evaluation_date=DATE)
    return dict(user=user, postulante=candidate, version=version, oferente=company, ofertas=offers, cursos=courses, categoria=category, contenido=content, perfil=profile, analisis=analysis, match=match, habilidades=evaluated, habilidades_duras=skills[:3], habilidades_blandas=skills[3:])
