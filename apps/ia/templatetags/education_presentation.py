"""Presentation helpers for education statuses and levels."""

from html import unescape

from django import template

register = template.Library()


@register.filter
def human_text(value):
    """Show legacy model text as Unicode; Django still escapes the result."""
    if value is None:
        return ""
    text = str(value)
    decoded = unescape(text)
    return unescape(decoded) if decoded != text else decoded


@register.filter
def education_status(item):
    if not isinstance(item, dict):
        return "Estado no informado"
    status = str(item.get("completion_status") or "unknown").casefold()
    labels = {
        "completed": "Finalizado",
        "in_progress": "En curso",
        "incomplete": "Incompleto",
    }
    if status in labels:
        return labels[status]
    if (str(item.get('level') or '').casefold() == 'bachelor'
            and any('cursad' in str(quote).casefold() for quote in item.get('source_quotes') or [])):
        return 'Cursado; título no informado'
    # Legacy profiles only have completed. False means not completed, but does
    # not establish whether the person is still studying or discontinued.
    if item.get("completed") is True:
        return "Finalizado"
    if item.get("completed") is False:
        return "No finalizado"
    return "Estado no informado"


@register.filter
def education_level(value):
    labels = {
        "secondary": "Secundario",
        "technical": "Tecnicatura",
        "bachelor": "Licenciatura",
        "master": "Maestría",
        "doctorate": "Doctorado",
        "other": "Otro estudio",
        "unknown": "Estudio",
    }
    return labels.get(str(value or "unknown").casefold(), "Estudio")


def _course_study(item):
    if not isinstance(item, dict) or str(item.get("level") or "").casefold() != "other":
        return False
    field = str(item.get("field") or "").strip().casefold()
    named_course = any(
        field == prefix or field.startswith((prefix + " ", prefix + ":", prefix + "-"))
        for prefix in ("curso", "taller", "seminario")
    )
    quotes = item.get('source_quotes') or []
    return named_course or any(isinstance(quote, str) and
        quote.strip().casefold().startswith(('curso ', 'curso:', 'taller ', 'seminario ')) for quote in quotes)


@register.filter
def academic_education(items):
    if not isinstance(items, (list, tuple)):
        return []
    return [item for item in items if isinstance(item, dict) and not _course_study(item)]


@register.filter
def course_education(items):
    if not isinstance(items, (list, tuple)):
        return []
    return [item for item in items if _course_study(item)]


@register.filter
def education_title(item):
    if not isinstance(item, dict):
        return "Estudio"
    level = str(item.get("level") or "unknown").casefold()
    field = str(item.get("field") or "").strip()
    if _course_study(item) and field:
        return field
    if level == 'other' and field:
        return field
    if level == 'bachelor' and field.casefold().startswith('lic. en '):
        return 'Licenciatura en ' + field[8:]
    title = "Grado universitario" if level == "bachelor" else education_level(level)
    normalized_field = field.casefold()
    # Some source records already carry the full program name in `field`.
    # Keep that wording without repeating the degree or upgrading bachelor to
    # a more specific credential such as Licenciatura.
    if field and normalized_field.startswith(title.casefold()):
        return field
    if level == "doctorate" and normalized_field.startswith("doctorado en "):
        return field
    return f"{title} en {field}" if field else title
