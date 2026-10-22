from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .forms import CuitField, RegistroOferenteForm
from .validators import normalizar_cuit, validar_cuit
from .uploads import CV_MAX_BYTES, normalize_image_upload, validate_cv_upload


class CuitFieldTests(SimpleTestCase):
    def test_acepta_once_digitos_con_o_sin_guiones(self):
        campo = CuitField()
        self.assertEqual(campo.clean('30123456789'), '30123456789')
        self.assertEqual(campo.clean('30-12345678-9'), '30-12345678-9')

    def test_rechaza_letras(self):
        with self.assertRaises(ValidationError):
            CuitField().clean('30-ABC45678-9')


class RegistroOferenteTests(TestCase):
    def test_registro_carga_filtro_de_cuit(self):
        response = self.client.get(reverse('registro') + '?tipo=oferente')

        self.assertContains(response, 'data-cuit-input')
        self.assertContains(response, 'cuit-input.js')
class CuitValidatorTests(TestCase):
    def test_acepta_cuit_valido_con_o_sin_guiones(self):
        for cuit in ('20-12345678-6', '20123456786'):
            validar_cuit(cuit)

    def test_rechaza_cuit_con_digito_verificador_incorrecto(self):
        with self.assertRaises(ValidationError):
            validar_cuit('20-12345678-7')

    def test_rechaza_cuit_con_longitud_incorrecta(self):
        with self.assertRaises(ValidationError):
            validar_cuit('20-1234-6')

    def test_rechaza_letras_y_prefijos_invalidos(self):
        for cuit in ('20-ABC12345678-6', '99-12345678-4'):
            with self.assertRaises(ValidationError):
                validar_cuit(cuit)

    def test_registro_normaliza_el_cuit(self):
        form = RegistroOferenteForm(data={
            'nombre_empresa': 'Empresa de prueba',
            'cuit': '20123456786',
            'email': 'empresa-cuit@example.com',
            'password1': 'Clave-segura-123!',
            'password2': 'Clave-segura-123!',
        })

        self.assertTrue(form.is_valid(), form.errors.as_json())
        self.assertEqual(form.cleaned_data['cuit'], '20-12345678-6')
        self.assertEqual(normalizar_cuit('20123456786'), '20-12345678-6')


class CVAndImageUploadValidationTests(SimpleTestCase):
    @staticmethod
    def _docx_with_external_relationship(relationship_type, target, *, macro=False):
        from io import BytesIO
        import zipfile
        from xml.sax.saxutils import quoteattr

        payload = BytesIO()
        with zipfile.ZipFile(payload, 'w') as archive:
            archive.writestr('[Content_Types].xml', '<Types/>')
            archive.writestr('word/document.xml',
                '<w:document xmlns:w="w"><w:body><w:p><w:r>'
                '<w:t>Experiencia en ventas y administración.</w:t>'
                '</w:r></w:p></w:body></w:document>')
            archive.writestr('word/settings.xml',
                '<w:settings xmlns:w="w" xmlns:r="r"><w:attachedTemplate r:id="rId1"/></w:settings>')
            archive.writestr('word/_rels/settings.xml.rels',
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/{relationship_type}" '
                f'TargetMode="External" Target={quoteattr(target)}/></Relationships>')
            if macro:
                archive.writestr('word/vbaProject.bin', b'macro')
        return SimpleUploadedFile('cv.docx', payload.getvalue())

    def test_docx_con_plantilla_remota_local_o_de_red_se_acepta_sin_modificarlo(self):
        for target in ('https://example.invalid/cv.dotx', 'file:///C:/plantillas/cv.dotm', r'\\servidor\plantillas\cv.dotx'):
            with self.subTest(target=target):
                upload = self._docx_with_external_relationship('attachedTemplate', target)
                original = upload.read()
                self.assertEqual(validate_cv_upload(upload)[0], 'docx')
                self.assertEqual(upload.tell(), 0)
                self.assertEqual(upload.read(), original)

    def test_docx_otros_recursos_externos_siguen_rechazados(self):
        for relationship_type in ('image', 'oleObject', 'aFChunk'):
            with self.subTest(relationship_type=relationship_type):
                upload = self._docx_with_external_relationship(relationship_type, 'https://example.invalid/resource')
                with self.assertRaisesMessage(ValidationError, 'recursos externos'):
                    validate_cv_upload(upload)

    def test_docx_plantilla_admitida_no_habilita_macros(self):
        upload = self._docx_with_external_relationship('attachedTemplate', 'https://example.invalid/cv.dotx', macro=True)
        with self.assertRaisesMessage(ValidationError, 'macros'):
            validate_cv_upload(upload)

    @override_settings(CV_LEGACY_CONVERTER_IMAGE='')
    def test_txt_utf8_es_admitido_y_extension_falsa_se_rechaza(self):
        upload = SimpleUploadedFile('cv.txt', 'Experiencia: Python'.encode())
        self.assertEqual(validate_cv_upload(upload)[0], 'txt')
        fake = SimpleUploadedFile('cv.txt', b'%PDF-1.7\n%%EOF')
        with self.assertRaises(ValidationError):
            validate_cv_upload(fake)

    def test_rechaza_un_byte_sobre_limite_cv(self):
        upload = SimpleUploadedFile('cv.txt', b'a' * (CV_MAX_BYTES + 1))
        with self.assertRaisesMessage(ValidationError, '5 MiB'):
            validate_cv_upload(upload)

    def test_txt_sobre_limite_de_extraccion_no_se_acepta(self):
        upload = SimpleUploadedFile('cv.txt', b'a' * 100_001)
        with self.assertRaisesMessage(ValidationError, '100.000'):
            validate_cv_upload(upload)

    def test_docx_con_xml_roto_se_rechaza_antes_de_guardar(self):
        from io import BytesIO
        import zipfile
        payload = BytesIO()
        with zipfile.ZipFile(payload, 'w') as archive:
            archive.writestr('[Content_Types].xml', '<Types/>')
            archive.writestr('word/document.xml', '<w:document><broken>')
        with self.assertRaises(ValidationError):
            validate_cv_upload(SimpleUploadedFile('cv.docx', payload.getvalue()))

    def test_docx_cuenta_separadores_de_parrafo_como_api_antes_de_guardar(self):
        from io import BytesIO
        import zipfile
        payload = BytesIO()
        document = (
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            '<w:p><w:r><w:t>' + ('a' * 50_000) + '</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>' + ('b' * 50_000) + '</w:t></w:r></w:p>'
            '</w:body></w:document>'
        )
        with zipfile.ZipFile(payload, 'w') as archive:
            archive.writestr('[Content_Types].xml', '<Types/>')
            archive.writestr('word/document.xml', document)
        with self.assertRaisesMessage(ValidationError, '100.000'):
            validate_cv_upload(SimpleUploadedFile('cv.docx', payload.getvalue()))

    def test_almacenamiento_privado_no_expone_url(self):
        from ia.models import private_cv_storage
        with self.assertRaises(ValueError):
            private_cv_storage.url('cv/privado.pdf')

    def test_imagen_4096_por_uno_se_normaliza_y_lado_4097_se_rechaza(self):
        from io import BytesIO
        from PIL import Image
        accepted = BytesIO()
        Image.new('RGB', (4096, 1), 'red').save(accepted, format='PNG')
        normalized = normalize_image_upload(
            SimpleUploadedFile('photo.png', accepted.getvalue()), max_bytes=2 * 1024 * 1024,
        )
        self.assertTrue(normalized.name.endswith('.webp'))
        oversized = BytesIO()
        Image.new('RGB', (4097, 1), 'red').save(oversized, format='PNG')
        with self.assertRaises(ValidationError):
            normalize_image_upload(
                SimpleUploadedFile('photo.png', oversized.getvalue()), max_bytes=2 * 1024 * 1024,
            )

    def test_formulario_admin_de_oferente_rechaza_gif(self):
        from io import BytesIO
        from PIL import Image
        from .admin import OferenteAdminForm
        image = BytesIO()
        Image.new('RGB', (2, 2), 'red').save(image, format='GIF')
        form = OferenteAdminForm()
        form.cleaned_data = {'logo': SimpleUploadedFile('logo.gif', image.getvalue())}
        with self.assertRaises(ValidationError):
            form.clean_logo()
