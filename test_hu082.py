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
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.storage.fallback import FallbackStorage
from usuarios.models import Usuario
from ofertas.models import TipoOferta, Habilidad, Oferta
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

def fresh_client():
    c = Client()
    c.force_login(user)
    return c

def get_messages(response):
    return [str(m) for m in response.wsgi_request._messages]

# Limpiar
Habilidad.objects.all().delete()
TipoOferta.objects.all().delete()
Oferta.objects.all().delete()

user = Usuario.objects.get(email='admin@test.com')

# Setup
tipo_tech = TipoOferta.objects.create(nombre='Tecnologia')
tipo_salud = TipoOferta.objects.create(nombre='Salud')

# === CA1 ===
print('=== CA1: Listar habilidades por tipo ===')
c = fresh_client()
response = c.get(f'/moderacion/tipos-oferta/{tipo_tech.id}/habilidades/')
test('Status 200', response.status_code == 200)
test('Tipo correcto', response.context['tipo'].id == tipo_tech.id)
test('Lista vacia', response.context['habilidades'].count() == 0)
print()

# === CA2 ===
print('=== CA2: Crear habilidad asociada a tipo ===')
c = fresh_client()
response = c.post(f'/moderacion/tipos-oferta/{tipo_tech.id}/habilidades/crear/', {'nombre': 'Python'})
test('Redirect al crear', response.status_code == 302)
test('Habilidad creada', Habilidad.objects.filter(nombre='Python', tipo_oferta=tipo_tech).exists())
print()

# === CA3 ===
print('=== CA3: No repetir nombre dentro del mismo tipo ===')
c = fresh_client()
response = c.post(f'/moderacion/tipos-oferta/{tipo_tech.id}/habilidades/crear/', {'nombre': 'Python'})
test('Rechaza duplicado mismo tipo', response.status_code != 302)
test('Solo 1 Python en Tecnologia', Habilidad.objects.filter(nombre='Python', tipo_oferta=tipo_tech).count() == 1)

c = fresh_client()
response = c.post(f'/moderacion/tipos-oferta/{tipo_salud.id}/habilidades/crear/', {'nombre': 'Python'})
test('Permite misma habilidad en tipo distinto', response.status_code == 302)
test('Python existe en Salud', Habilidad.objects.filter(nombre='Python', tipo_oferta=tipo_salud).exists())
print()

# === CA4 ===
print('=== CA4: Sin tipos de oferta, mostrar mensaje ===')
TipoOferta.objects.all().delete()
c = fresh_client()
response = c.get('/moderacion/tipos-oferta/')
test('Status 200 sin tipos', response.status_code == 200)
test('Mensaje vacio', 'No hay tipos de oferta cargados' in response.content.decode())

tipo_tech = TipoOferta.objects.create(nombre='Tecnologia')
tipo_salud = TipoOferta.objects.create(nombre='Salud')
print()

# === CA5 ===
print('=== CA5: Editar habilidad ===')
c = fresh_client()
hab = Habilidad.objects.create(nombre='JavaScript', tipo_oferta=tipo_tech)
response = c.post(f'/moderacion/habilidades/{hab.id}/modificar/', {'nombre': 'JavaScript ES6'})
test('Redirect al editar', response.status_code == 302)
test('Nombre actualizado', Habilidad.objects.filter(nombre='JavaScript ES6', tipo_oferta=tipo_tech).exists())
test('Nombre anterior eliminado', not Habilidad.objects.filter(nombre='JavaScript', tipo_oferta=tipo_tech).exists())

c = fresh_client()
response = c.post(f'/moderacion/habilidades/{hab.id}/modificar/', {'nombre': 'JavaScript ES6'})
test('Permite mismo nombre', response.status_code == 302)

# Crear otra habilidad y intentar duplicar
c = fresh_client()
hab2 = Habilidad.objects.create(nombre='React', tipo_oferta=tipo_tech)
response = c.post(f'/moderacion/habilidades/{hab2.id}/modificar/', {'nombre': 'JavaScript ES6'})
test('Rechaza duplicado en edicion', response.status_code != 302)
test('Form tiene errores', bool(response.context['form'].errors) if response.context else False)
print()

# === CA7 ===
print('=== CA7: No eliminar si esta en oferta ===')
c = fresh_client()
hab_django = Habilidad.objects.create(nombre='Django', tipo_oferta=tipo_tech)
oferta = Oferta.objects.create(
    empresa=user, tipo_oferta=tipo_tech,
    titulo='Oferta Test', nombre_puesto='Dev', ubicacion='BA',
    modalidad='remoto', descripcion='Test',
    habilidades_requeridas='Python,Django,REST',
    nivel_educativo='universitario',
    fecha_cierre=timezone.now() + timedelta(days=30), estado='activa'
)
response = c.post(f'/moderacion/habilidades/{hab_django.id}/baja/')
test('Redirect al intentar eliminar', response.status_code == 302)
test('Habilidad sigue existiendo', Habilidad.objects.filter(nombre='Django', tipo_oferta=tipo_tech).exists())
print()

# === CA8 ===
print('=== CA8: Mensajes de confirmacion ===')
c = Client()
c.force_login(user)

# Crear
response = c.post(f'/moderacion/tipos-oferta/{tipo_tech.id}/habilidades/crear/', {'nombre': 'React'})
test('React creado', Habilidad.objects.filter(nombre='React', tipo_oferta=tipo_tech).exists())

# Editar
react = Habilidad.objects.get(nombre='React', tipo_oferta=tipo_tech)
response = c.post(f'/moderacion/habilidades/{react.id}/modificar/', {'nombre': 'ReactJS'})
test('ReactJS editado', Habilidad.objects.filter(nombre='ReactJS', tipo_oferta=tipo_tech).exists())

# Eliminar
react = Habilidad.objects.get(nombre='ReactJS', tipo_oferta=tipo_tech)
response = c.post(f'/moderacion/habilidades/{react.id}/baja/')
test('ReactJS eliminado', not Habilidad.objects.filter(nombre='ReactJS', tipo_oferta=tipo_tech).exists())
print()

# === Verificar listado final ===
print('=== Verificar listado final ===')
c = fresh_client()
response = c.get(f'/moderacion/tipos-oferta/{tipo_tech.id}/habilidades/')
content = response.content.decode()
test('JavaScript ES6 en listado', 'JavaScript ES6' in content)
test('Django en listado', 'Django' in content)
print()

print(f'========================================')
print(f'RESULTADO: {passed} PASS / {failed} FAIL')
print(f'========================================')
