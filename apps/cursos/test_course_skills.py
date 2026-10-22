from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from categorias.models import Categoria as SkillCategory, Habilidad
from .forms import CursoForm
from .models import Categoria, Curso


class CursoHabilidadesFormTests(TestCase):
    def setUp(self):
        self.course_category = Categoria.objects.create(nombre='Cursos generales')
        self.skill_category = SkillCategory.objects.create(nombre='Competencias técnicas')
        self.other_skill_category = SkillCategory.objects.create(nombre='Competencias transversales')
        self.python = Habilidad.objects.create(categoria=self.skill_category, nombre='Python')
        self.comunicacion = Habilidad.objects.create(
            categoria=self.other_skill_category, nombre='Comunicación', tipo_habilidad='B'
        )

    def _valid_data(self, **overrides):
        data = {
            'nombre': 'Introducción a tecnología',
            'categoria': self.course_category.pk,
            'descripcion': 'Curso práctico para desarrollar competencias con contenidos declarados.',
            'duracion': '8 semanas',
            'horario': 'A coordinar',
            'tipo': Curso.VIRTUAL,
            'url_externa': '',
        }
        data.update(overrides)
        return data

    @staticmethod
    def _valid_image():
        image = Image.new('RGB', (2, 2), color='white')
        contents = BytesIO()
        image.save(contents, format='PNG')
        return SimpleUploadedFile('curso.png', contents.getvalue(), content_type='image/png')

    def test_create_form_saves_multiple_skills_from_different_categories(self):
        form = CursoForm(
            self._valid_data(habilidades=[self.python.pk, self.comunicacion.pk]),
            {'imagen': self._valid_image()},
        )
        self.assertTrue(form.is_valid(), form.errors)

        curso = form.save()
        self.addCleanup(lambda: curso.imagen.delete(save=False))
        self.assertSetEqual(set(curso.habilidades.all()), {self.python, self.comunicacion})
        self.assertEqual(curso.habilidades.count(), 2)

    def test_edit_form_replaces_selected_skills_and_inactive_course_keeps_them(self):
        curso = Curso.objects.create(
            nombre='Curso previo', categoria=self.course_category,
            imagen='cursos/previo.png', descripcion='Descripción anterior',
            duracion='6 semanas', horario='A coordinar', tipo=Curso.PRESENCIAL,
        )
        curso.habilidades.add(self.python)
        form = CursoForm(
            self._valid_data(nombre='Curso actualizado', habilidades=[self.comunicacion.pk]),
            instance=curso,
        )
        self.assertTrue(form.is_valid(), form.errors)

        curso = form.save()
        self.assertSetEqual(set(curso.habilidades.all()), {self.comunicacion})
        curso.activo = False
        curso.save(update_fields=['activo'])
        self.assertSetEqual(set(curso.habilidades.all()), {self.comunicacion})

    def test_skills_are_optional_and_empty_submission_remains_valid(self):
        form = CursoForm(self._valid_data(), {'imagen': self._valid_image()})
        self.assertFalse(form.fields['habilidades'].required)
        self.assertEqual(form.fields['habilidades'].label, 'Habilidades que desarrolla')
        self.assertTrue(form.is_valid(), form.errors)

        curso = form.save()
        self.addCleanup(lambda: curso.imagen.delete(save=False))
        self.assertFalse(curso.habilidades.exists())
