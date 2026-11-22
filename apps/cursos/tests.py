from django.test import SimpleTestCase, TestCase
from django.core.exceptions import ValidationError
from .forms import CourseScheduleField, CursoForm
from django.urls import reverse

from .models import Categoria, Curso


class CourseOfficialLinkTests(TestCase):
    def setUp(self):
        self.course = Curso.objects.create(
            nombre='Curso de prueba', categoria=Categoria.objects.create(nombre='Tecnología'),
            descripcion='Descripción de prueba', duracion='8 semanas', horario='Martes 18 h',
        )

    def test_links_to_exact_course_page_in_a_new_tab(self):
        self.course.url_externa = 'https://ien.edu.ar/cursos/curso-de-prueba/'
        self.course.save(update_fields=['url_externa'])
        response = self.client.get(reverse('cursos:detalle', args=[self.course.pk]))
        self.assertContains(response, f'href="{self.course.url_externa}" target="_blank" rel="noopener noreferrer"')
        self.assertContains(response, 'Ver curso en el IEN')
        self.assertNotContains(response, 'El enlace oficial de este curso todavía no fue cargado.')

    def test_without_official_url_does_not_invent_a_destination(self):
        response = self.client.get(reverse('cursos:detalle', args=[self.course.pk]))
        self.assertContains(response, 'disabled aria-describedby="curso-enlace-ayuda"')
        self.assertContains(response, 'El enlace oficial de este curso todavía no fue cargado.')
        self.assertNotContains(response, 'href="https://ien.edu.ar/cursos/')



class CourseFormControlTests(SimpleTestCase):
    def test_schedule_orders_days_and_formats_times(self):
        self.assertEqual(CourseScheduleField().clean([['Viernes', 'Lunes'], '09:00', '11:30']),
                         'Lunes, Viernes de 09:00 a 11:30')

    def test_schedule_rejects_missing_days_or_times_and_reversed_range(self):
        for values in (([], '09:00', '10:00'), (['Lunes'], '', '10:00'),
                       (['Lunes'], '10:00', '09:00'), (['Lunes'], '10:00', '10:00')):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                CourseScheduleField().clean(values)

    def test_schedule_round_trips_when_editing(self):
        field = CourseScheduleField()
        value = 'Martes, Jueves de 18:00 a 20:00'
        self.assertEqual(field.clean(field.widget.decompress(value)), value)

    def test_image_is_optional_and_controls_render_without_native_multi_selection(self):
        form = CursoForm()
        form.fields['categoria'].choices = [('', 'Elegir categoría')]
        form.fields['habilidades'].choices = [('1', 'Python'), ('2', 'Excel')]
        self.assertFalse(form.fields['imagen'].required)
        self.assertIn('comunicacion-predeterminada.webp', str(form['imagen']))
        self.assertIn('data-skill-add', str(form['habilidades']))
        self.assertIn('name="horario_0"', str(form['horario']))
        self.assertIn('type="time"', str(form['horario']))

    def test_legacy_schedule_is_explained_without_guessing_times(self):
        form = CursoForm(initial={'horario': 'Todos los días por la tarde'})
        self.assertIn('Todos los días por la tarde', form.fields['horario'].help_text)
        self.assertEqual(form.fields['horario'].widget.decompress(form.initial['horario']), [[], None, None])


class StructuredCourseSaveTests(TestCase):
    def test_course_saves_multiple_skills_and_schedule_without_an_image(self):
        from categorias.models import Habilidad
        category = Categoria.objects.create(nombre='Datos')
        skills = [Habilidad.objects.create(nombre=name, categoria=category) for name in ('Python', 'Excel')]
        form = CursoForm(data={
            'nombre': 'Análisis de datos', 'categoria': category.pk, 'descripcion': 'Curso práctico de análisis de datos.',
            'duracion': '8 semanas', 'tipo': 'Virtual', 'horario_0': ['Martes', 'Jueves'],
            'horario_1': '18:00', 'horario_2': '20:00', 'habilidades': [skill.pk for skill in skills],
        })
        self.assertTrue(form.is_valid(), form.errors)
        course = form.save()
        self.assertFalse(course.imagen)
        self.assertEqual(course.horario, 'Martes, Jueves de 18:00 a 20:00')
        self.assertEqual(set(course.habilidades.values_list('pk', flat=True)), {skill.pk for skill in skills})
        edit = CursoForm(instance=course)
        self.assertEqual(edit.fields['horario'].widget.decompress(edit.initial['horario']), [['Martes', 'Jueves'], '18:00', '20:00'])


class CourseDefaultCoverTests(SimpleTestCase):
    def test_three_shared_photos_match_course_topics(self):
        from .covers import course_cover_path
        for title, category, theme in [
            ('Python desde cero', '', 'tecnologia'),
            ('Excel avanzado', 'Tecnología', 'administracion'),
            ('Redes sociales y marketing', '', 'comunicacion'),
            ('Curso nuevo', 'Administración', 'administracion'),
            ('Curso nuevo', '', 'comunicacion'),
        ]:
            with self.subTest(title=title):
                self.assertEqual(course_cover_path(title, category), f'images/cursos/{theme}-predeterminada.webp')

    def test_public_card_uses_default_without_querying_category(self):
        from django.template.loader import render_to_string
        course = Curso(nombre='Python inicial', categoria_id=999)
        html = render_to_string('cursos/_cover.html', {'curso': course})
        self.assertIn('tecnologia-predeterminada.webp', html)

    def test_uploaded_image_takes_precedence(self):
        from django.template.loader import render_to_string
        course = Curso(nombre='Excel', imagen='cursos/propia.webp')
        html = render_to_string('cursos/_cover.html', {'curso': course})
        self.assertIn('src="/media/cursos/propia.webp"', html)
        self.assertNotIn('src="/static/images/cursos/', html)
