"""Three shared photographic covers; an uploaded image always takes priority."""
import re
import unicodedata

COVER_THEMES = ('tecnologia', 'administracion', 'comunicacion')
COVER_RULES = (
    ('administracion', r'excel|administr|contab|finan|planilla|gestion'),
    ('comunicacion', r'comunic|marketing|social|atencion|ventas|equipo|entrevista'),
    ('tecnologia', r'python|django|sql|program|datos|sistema|tecnolog|informat|desarrollo|web|ciber|redes|java|react'),
)


def course_cover_theme(title='', category=''):
    for value in (title, category):
        text = ''.join(c for c in unicodedata.normalize('NFD', value or '').casefold() if not unicodedata.combining(c))
        for theme, pattern in COVER_RULES:
            if re.search(pattern, text):
                return theme
    return 'comunicacion'


def course_cover_path(title='', category=''):
    return f'images/cursos/{course_cover_theme(title, category)}-predeterminada.webp'


def cached_category_name(course):
    """Don't introduce a database query per card merely to choose a cover."""
    category = getattr(getattr(course, '_state', None), 'fields_cache', {}).get('categoria')
    return getattr(category, 'nombre', '')
