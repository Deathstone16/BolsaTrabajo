"""Read-only course suggestions for historical match gaps and today's catalog.

Catalog/title evidence suggests relevance, never that a course grants a degree,
license, experience or a new match score. Category-only fallbacks are navigation
options explicitly labelled as unverified coverage.
"""

import re
import unicodedata

from cursos.models import Curso


_STATUS_ORDER = {'not_met': 0, 'partial': 1, 'unknown': 2}
_STATUS_LABELS = {'not_met': 'No alcanzado', 'partial': 'Parcial', 'unknown': 'Sin información'}
_MATCH_ORDER = {'title': 0, 'skill': 1, 'description': 2, 'related': 3}
_TRAINABLE = {'technical_skills', 'soft_skills', 'languages', 'desirables'}
_STOP_WORDS = {
    'a', 'de', 'del', 'la', 'el', 'los', 'las', 'al', 'en', 'con', 'para',
    'conocimiento', 'conocimientos', 'manejo', 'dominio', 'uso', 'nivel',
    'basico', 'basica', 'intermedio', 'intermedia', 'avanzado', 'avanzada',
}
_GENERAL_WORDS = {'curso', 'cursos', 'taller', 'introduccion', 'general', 'generales',
                  'inicial', 'fundamentos', 'capacitacion', 'programa', 'formacion'}
_CONTEXT_EXCLUSIONS = {'no', 'sin', 'excepto', 'excluye', 'requisito', 'requisitos',
                       'prerrequisito', 'prerrequisitos', 'requiere', 'requieren',
                       'requerido', 'requeridos', 'previo', 'previos', 'previa', 'previas'}


def _words(value):
    text = unicodedata.normalize('NFKD', str(value or '')).casefold()
    text = ''.join(char for char in text if not unicodedata.combining(char))
    # Preserve C++/C# while avoiding Java/JavaScript and R/React substrings.
    return tuple(re.findall(r'[a-z0-9]+(?:\+\+|#)?', text))


def _subject(value):
    words = tuple(word for word in _words(value) if word not in _STOP_WORDS)
    if len(words) == 2 and words[0] in {'microsoft', 'ms'} and words[1] in {
        'excel', 'word', 'powerpoint', 'outlook', 'access',
    }:
        return words[1:]
    return words


def _mentions(subject, value):
    words = _subject(value)
    if not subject:
        return False
    for index in range(len(words) - len(subject) + 1):
        if words[index:index + len(subject)] == subject:
            # Do not treat explicit exclusions/prerequisites as coverage.
            if not set(words[max(0, index - 3):index]) & _CONTEXT_EXCLUSIONS:
                return True
    return False


def _trainable(requirement):
    if requirement.get('category') not in _TRAINABLE:
        return False
    words = _words(requirement.get('name'))
    if not words or set(words) & {'licencia', 'licencias', 'carnet', 'matricula', 'habilitacion',
                                 'licenciatura', 'doctorado', 'maestria', 'bachillerato'}:
        return False
    if 'titulo' in words and set(words) & {'universitario', 'universitaria', 'terciario', 'profesional'}:
        return False
    years = requirement.get('minimum_years')
    if years is not None:
        try:
            if float(years) > 0:
                return False
        except (ValueError, TypeError):
            return False
    name = ' '.join(words)
    if re.search(r'\b(?:\d+|un|uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+(?:anos?|meses|years?|months?)\b', name):
        return False
    return bool(_subject(requirement.get('name')))


def _gaps(match):
    snapshot = match.offer_snapshot if isinstance(match.offer_snapshot, dict) else {}
    requirements = snapshot.get('requirements') or []
    requirements = requirements if isinstance(requirements, list) else []
    by_id = {item.get('id'): item for item in requirements if isinstance(item, dict) and item.get('id')}
    result = match.resultado if isinstance(match.resultado, dict) else {}
    assessments = result.get('assessments') or []
    if not isinstance(assessments, list):
        return []
    gaps, seen = [], set()
    for index, assessment in enumerate(assessments):
        if not isinstance(assessment, dict) or assessment.get('status') not in _STATUS_ORDER:
            continue
        requirement_id = assessment.get('requirement_id')
        if requirements:
            if requirement_id is None:
                candidates = [
                    item for item in requirements if isinstance(item, dict)
                    and _words(item.get('name')) == _words(assessment.get('name'))
                    and item.get('category') == assessment.get('category')
                ]
                requirement = candidates[0] if len(candidates) == 1 else None
            else:
                requirement = by_id.get(requirement_id)
            if requirement is None:
                continue  # Never replace a frozen requirement with current offer fields.
        else:
            requirement = assessment  # Legacy results without a requirements snapshot.
        if not _trainable(requirement):
            continue
        key = requirement_id or (_subject(requirement.get('name')), requirement.get('category'))
        if key in seen:
            continue
        seen.add(key)
        status = assessment['status']
        gaps.append({
            'requirement_id': requirement_id, 'name': str(requirement['name']),
            'category': requirement['category'], 'mandatory': bool(requirement.get('mandatory', False)),
            'status': status, 'status_label': _STATUS_LABELS[status], 'optional': status == 'unknown',
            'courses': [], '_index': index,
        })
    gaps.sort(key=lambda gap: (_STATUS_ORDER[gap['status']], not gap['mandatory'], gap['_index']))
    for gap in gaps:
        gap.pop('_index')
    return gaps


def _specific(course, gap):
    subject = _subject(gap['name'])
    if _mentions(subject, course.nombre):
        return 'title', f'El título del curso menciona {gap["name"]}.'
    if any(_subject(skill.nombre) == subject for skill in course.habilidades.all()):
        return 'skill', f'El catálogo vincula este curso con la habilidad {gap["name"]}.'
    if _mentions(subject, course.descripcion):
        return 'description', f'La descripción del curso menciona {gap["name"]}.'
    return None


def _general(course, area):
    if not area or course.categoria_id != area.pk:
        return False
    title = tuple(word for word in _subject(course.nombre) if word not in _GENERAL_WORDS)
    area_name = tuple(word for word in _subject(area.nombre) if word not in _GENERAL_WORDS)
    return bool(area_name) and title == area_name


def _reason(gap, evidence):
    if gap['optional']:
        return f'Sugerencia opcional: no hay información suficiente sobre {gap["name"]}. {evidence}'
    return f'Para reforzar {gap["name"]}. {evidence}'


def recommend_courses_for_match(match):
    """Return max 3 references per gap and 6 unique cards, without writing data.

    ``courses`` is the unique card list; gap-local entries reference those same
    course objects. ``no_catalog`` means there are no active catalog entries;
    an active catalog without relevant courses instead returns empty cards.
    """
    empty = {'gaps': [], 'courses': [], 'has_gaps': False, 'no_catalog': False}
    if match.estado != 'completed':
        return empty
    gaps = _gaps(match)
    if not gaps:
        return empty
    catalog = list(Curso.objects.filter(activo=True).select_related('categoria').prefetch_related('habilidades'))
    # The catalog and navigation area are current; gap identity/classification
    # above is frozen in the completed match's offer_snapshot.
    area = match.oferta.categoria
    cards = {}
    for gap in gaps:
        ranked = []
        for course in catalog:
            specific = _specific(course, gap)
            if specific:
                kind, evidence = specific
                ranked.append((course, kind, evidence))
        if not ranked:
            ranked = [
                (course, 'related', 'Opción general del área de la oferta; '
                 f'revisá si su temario cubre {gap["name"]}.')
                for course in catalog if _general(course, area)
            ]
        ranked.sort(key=lambda item: (_MATCH_ORDER[item[1]], _words(item[0].nombre), item[0].pk))
        for course, kind, evidence in ranked:
            if len(gap['courses']) >= 3:
                break
            if course.pk not in cards and len(cards) >= 6:
                continue
            reason = _reason(gap, evidence)
            reference = {'course': course, 'match_type': kind, 'reason': reason}
            gap['courses'].append(reference)
            detail = {key: gap[key] for key in ('requirement_id', 'name', 'status', 'status_label', 'mandatory', 'optional')}
            if course.pk not in cards:
                cards[course.pk] = {**reference, 'gaps': [detail], 'optional': gap['optional']}
            else:
                card = cards[course.pk]
                card['gaps'].append(detail)
                card['reason'] += ' ' + reason
                card['optional'] = card['optional'] and gap['optional']
                if _MATCH_ORDER[kind] < _MATCH_ORDER[card['match_type']]:
                    card['match_type'] = kind
    return {'gaps': gaps, 'courses': list(cards.values()), 'has_gaps': True, 'no_catalog': not catalog}
