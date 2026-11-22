from django import template
from cursos.covers import course_cover_path, cached_category_name
from ientrabajo.templatetags.ien_static import static_v

register = template.Library()


@register.simple_tag
def course_default_cover(course):
    return static_v(course_cover_path(getattr(course, 'nombre', ''), cached_category_name(course)))
