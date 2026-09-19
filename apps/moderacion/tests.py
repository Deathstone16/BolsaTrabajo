from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from ofertas.models import Oferta
from usuarios.models import Oferente, Usuario


class RechazarOfertaTests(TestCase):
    def setUp(self):
        self.staff = Usuario.objects.create_user(
            email='moderador@example.com', password='clave-segura', is_staff=True,
        )
        empresa = Usuario.objects.create_user(
            email='empresa-moderada@example.com', password='clave-segura',
        )
        Oferente.objects.create(
            usuario=empresa,
            nombre_empresa='Empresa de prueba',
            cuit='30-12345678-9',
            estado_validacion=Oferente.EstadoValidacion.APROBADO,
        )
        categoria = Categoria.objects.create(nombre='Tecnología')
        self.oferta = Oferta.objects.create(
            empresa=empresa,
            categoria=categoria,
            titulo='Desarrollador', nombre_puesto='Desarrollador',
            ubicacion='Córdoba', descripcion='Descripción de prueba',
            habilidades_requeridas='Python', habilidades_duras='Python',
            nivel_educativo='universitario',
            fecha_cierre=timezone.now() + timedelta(days=10),
        )
        self.client.force_login(self.staff)

    def test_rechazo_exige_motivo(self):
        response = self.client.post(reverse('mod_rechazar_oferta', args=[self.oferta.id]))
        self.assertEqual(response.status_code, 400)
        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.estado, 'pendiente')

    def test_rechazo_guarda_motivo(self):
        response = self.client.post(
            reverse('mod_rechazar_oferta', args=[self.oferta.id]), {'motivo': 'Datos incompletos'},
        )
        self.assertEqual(response.status_code, 200)
        self.oferta.refresh_from_db()
        self.assertEqual(self.oferta.estado, 'rechazada')
        self.assertEqual(self.oferta.motivo_rechazo, 'Datos incompletos')
