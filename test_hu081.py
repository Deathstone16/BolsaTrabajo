import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'ientrabajo.settings.base'
sys.path.insert(0, os.path.join(os.getcwd(), 'apps'))

from django.conf import settings
settings.DEBUG = True
settings.ALLOWED_HOSTS = ['*']

import django
django.setup()

from django.test.utils import setup_test_environment
setup_test_environment()

from django.test import Client
from django.test.client import RequestFactory
from usuarios.models import Usuario
from ofertas.models import TipoOferta, Oferta
from ofertas.services import puede_eliminar_tipo_oferta
from django.utils import timezone
from datetime import timedelta

passed = 0
failed = 0

def test(name, condition, msg=''):
    global passed, failed
    if condition:
        passed += 1
        print(f'  PASS - {name}')
    else:
        failed += 1
        print(f'  FAIL - {name}: {msg}')

# Limpiar
TipoOferta.objects.all().delete()
Oferta.objects.all().delete()

user = Usuario.objects.get(email='admin@test.com')

# === CA1 ===
print('=== CA1: Listar tipos de oferta ===')
client = Client()
client.force_login(user)
response = client.get('/moderacion/tipos-oferta/')
test('Status 200', response.status_code == 200, f'Got {response.status_code}')

# === CA2 ===
print()
print('=== CA2: Crear tipo con nombre unico ===')
client2 = Client()
client2.force_login(user)

response = client2.post('/moderacion/tipos-oferta/crear/', {'nombre': 'Tecnologia'})
test('Redirect al crear', response.status_code == 302, f'Got {response.status_code}')
test('Tipo creado', TipoOferta.objects.filter(nombre='Tecnologia').exists())

response = client2.post('/moderacion/tipos-oferta/crear/', {'nombre': 'Tecnologia'})
test('Rechaza duplicado', response.status_code != 302, f'Got {response.status_code} (should not redirect)')
test('Solo 1 Tecnologia', TipoOferta.objects.filter(nombre='Tecnologia').count() == 1)

# === CA3 ===
print()
print('=== CA3: Validacion minimo 3 caracteres ===')
client3 = Client()
client3.force_login(user)

response = client3.post('/moderacion/tipos-oferta/crear/', {'nombre': 'AB'})
test('Rechaza 2 caracteres', response.status_code != 302)

response = client3.post('/moderacion/tipos-oferta/crear/', {'nombre': ''})
test('Rechaza vacio', response.status_code != 302)

response = client3.post('/moderacion/tipos-oferta/crear/', {'nombre': 'Salud'})
test('Acepta 5 caracteres', response.status_code == 302)
test('Salud creado', TipoOferta.objects.filter(nombre='Salud').exists())

# === CA4 ===
print()
print('=== CA4: Editar tipo de oferta ===')
client4 = Client()
client4.force_login(user)

tipo = TipoOferta.objects.get(nombre='Salud')
response = client4.post(f'/moderacion/tipos-oferta/{tipo.id}/modificar/', {'nombre': 'Salud Publica'})
test('Redirect al editar', response.status_code == 302, f'Got {response.status_code}')
test('Nombre actualizado', TipoOferta.objects.filter(nombre='Salud Publica').exists())
test('Nombre anterior eliminado', not TipoOfleta.objects.get_queryset().filter(nombre='Salud').exists() if False else not TipoOferta.objects.filter(nombre='Salud').exists())

# Editar sin cambiar nombre (instance excluye a si mismo)
response = client4.post(f'/moderacion/tipos-oferta/{tipo.id}/modificar/', {'nombre': 'Salud Publica'})
test('Permite mismo nombre', response.status_code == 302)

otro = TipoOferta.objects.get(nombre='Tecnologia')
response = client4.post(f'/moderacion/tipos-oferta/{otro.id}/modificar/', {'nombre': 'Salud Publica'})
test('Rechaza duplicado en edicion', response.status_code != 302)

# === CA6 ===
print()
print('=== CA6: No eliminar si tiene ofertas asociadas ===')
client6 = Client()
client6.force_login(user)

oferta = Oferta.objects.create(
    empresa=user,
    tipo_oferta=TipoOferta.objects.get(nombre='Tecnologia'),
    titulo='Oferta Test',
    nombre_puesto='Dev',
    ubicacion='BA',
    modalidad='remoto',
    descripcion='Test',
    habilidades_requeridas='Python',
    nivel_educativo='universitario',
    fecha_cierre=timezone.now() + timedelta(days=30),
    estado='activa'
)
puede = puede_eliminar_tipo_oferta(oferta.tipo_oferta.id)
test('No puede eliminar con ofertas', not puede, f'puede={puede}')

response = client6.post(f'/moderacion/tipos-oferta/{oferta.tipo_oferta.id}/baja/')
test('Redirect al intentar eliminar', response.status_code == 302)
test('Tipo sigue existiendo', TipoOferta.objects.filter(nombre='Tecnologia').exists())

tipo_eliminar = TipoOferta.objects.get(nombre='Salud Publica')
response = client6.get(f'/moderacion/tipos-oferta/{tipo_eliminar.id}/baja/')
test('Muestra confirmacion', response.status_code == 200)
response = client6.post(f'/moderacion/tipos-oferta/{tipo_eliminar.id}/baja/')
test('Elimina exitosamente', response.status_code == 302)
test('Nombre eliminado de BD', not TipoOferta.objects.filter(nombre='Salud Publica').exists())

# === CA7 ===
print()
print('=== CA7: Mensajes de confirmacion ===')
client7 = Client()
client7.force_login(user)

response = client7.post('/moderacion/tipos-oferta/crear/', {'nombre': 'Construccion'})
msgs = [str(m) for m in response.wsgi_request._messages]
test('Mensaje creacion', any('creado' in m.lower() for m in msgs), f'Messages: {msgs}')

construccion = TipoOferta.objects.get(nombre='Construccion')
response = client7.post(f'/moderacion/tipos-oferta/{construccion.id}/modificar/', {'nombre': 'Construccion Civil'})
msgs = [str(m) for m in response.wsgi_request._messages]
test('Mensaje edicion', any('modificado' in m.lower() for m in msgs), f'Messages: {msgs}')

construccion = TipoOferta.objects.get(nombre='Construccion Civil')
response = client7.post(f'/moderacion/tipos-oferta/{construccion.id}/baja/')
msgs = [str(m) for m in response.wsgi_request._messages]
test('Mensaje eliminacion', any('eliminado' in m.lower() for m in msgs), f'Messages: {msgs}')

# === Listar final ===
print()
print('=== TEST: Listar muestra tipos ===')
client8 = Client()
client8.force_login(user)
response = client8.get('/moderacion/tipos-oferta/')
content = response.content.decode()
test('Tecnologia en listado', 'Tecnologia' in content)
test('Construccion Civil NO en listado (fue eliminado)', 'Construccion Civil' not in content)

print()
print(f'========================================')
print(f'RESULTADO: {passed} PASS / {failed} FAIL')
print(f'========================================')
