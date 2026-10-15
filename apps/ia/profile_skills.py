"""Presentación de habilidades del perfil de CV sin alterar el contrato de IA."""

import unicodedata


SOFT_SKILL_NAMES = {
    'adaptability', 'adaptabilidad',
    'analytical thinking', 'pensamiento analitico',
    'attention to detail', 'atencion al detalle',
    'collaboration', 'colaboracion',
    'communication', 'comunicacion',
    'conflict resolution', 'resolucion de conflictos',
    'creativity', 'creatividad',
    'critical thinking', 'pensamiento critico',
    'emotional intelligence', 'inteligencia emocional',
    'empathy', 'empatia',
    'initiative', 'iniciativa',
    'leadership', 'liderazgo',
    'negotiation', 'negociacion',
    'organization', 'organizacion',
    'problem solving', 'resolucion de problemas',
    'resilience', 'resiliencia',
    'teamwork', 'trabajo en equipo',
    'time management', 'gestion del tiempo',
}


def _normalized_name(value):
    unaccented = unicodedata.normalize('NFKD', str(value or ''))
    return ' '.join(''.join(char for char in unaccented if not unicodedata.combining(char)).casefold().split())


def split_profile_skills(content):
    """Agrupa etiquetas blandas conocidas; conserva las demás sin inventar categorías."""
    hard, soft = [], []
    skills = content.get('skills', []) if isinstance(content, dict) else []
    for skill in skills if isinstance(skills, list) else []:
        if not isinstance(skill, dict):
            continue
        (soft if _normalized_name(skill.get('name')) in SOFT_SKILL_NAMES else hard).append(skill)
    return hard, soft
