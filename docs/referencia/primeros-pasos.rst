Primeros pasos
==============

Nota de vigencia: esta página conserva el inicio breve original. El procedimiento completo y mantenido está en ``README.md`` y ``docs/inicio/proyecto.md``.


Requisitos
----------

* Python 3.11.
* Dependencias de la aplicación en ``requirements.txt``.
* Para compilar la documentación, instalar ``requirements-dev.txt``; este
  archivo incluye Sphinx, el tema Read the Docs y MyST Parser.
* Para la aplicación completa, PostgreSQL y Redis. En desarrollo se puede usar
  SQLite, pero producción requiere PostgreSQL.
* El servicio FastAPI del repositorio ``ia_api/backend`` para extracción de CV,
  normalización de perfiles y análisis de ofertas. Consultá sus variables en su
  ``.env.example`` y la configuración de despliegue en
  :doc:`DESPLIEGUE_VPS </DESPLIEGUE_VPS>`.

Preparación local
-----------------

Crear y activar un entorno virtual desde la raíz del repositorio. En Windows::

   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt

Configurar las variables de entorno necesarias en ``.env``. Para desarrollo
local, Django usa SQLite si no se define ``DB_ENGINE``; para PostgreSQL,
definir ``DB_ENGINE=postgresql`` y ``DB_NAME``, ``DB_USER``, ``DB_PASSWORD``
y ``DB_HOST``. Las llamadas a la API requieren ``IA_API_URL`` y el token de
servicio compartido ``IA_API_TOKEN``. Aplicar migraciones e iniciar Django::

   python manage.py migrate
   python manage.py runserver

La API se inicia por separado desde su directorio ``backend``; su README
describe los modos de ejecución y configuración. Para que el flujo de punta a
punta funcione, también deben estar activos Redis, el worker Celery de la API
y los despachadores de extracción y matching de Django.

Flujo funcional
---------------

1. El postulante carga un CV. Django valida la solicitud, limita el tamaño y,
   si el escaneo está habilitado, analiza el archivo antes de guardarlo en una
   ubicación privada.
2. Django crea una versión del CV, un trabajo de extracción y un evento de
   salida. El despachador entrega el snapshot del archivo a FastAPI con
   autenticación Bearer e idempotencia.
3. FastAPI extrae y estructura la información del documento. Celery ejecuta
   el trabajo fuera del proceso HTTP y devuelve el resultado mediante un
   callback autenticado con HMAC.
4. Django guarda el perfil profesional extraído. La normalización puede
   enriquecerlo con contexto de habilidades y conservar la procedencia de los
   datos para revisión y edición por el postulante.
5. Al comparar el perfil con una oferta, Django envía snapshots a FastAPI. El
   análisis de compatibilidad vuelve como trabajo asíncrono; el resultado
   registra estados y evidencias para los requisitos de la oferta.
6. Para un match completado, Django recomienda cursos activos según las
   brechas entrenables y sus evidencias. Las recomendaciones son referencias
   del catálogo y no modifican el resultado del match.

Comprobaciones
--------------

Para revisar la configuración de Django y ejecutar sus pruebas::

   python manage.py check
   python manage.py test

Generar esta documentación
--------------------------

Instalar las dependencias de desarrollo y compilar el sitio HTML::

   python -m pip install -r requirements-dev.txt
   python -m sphinx -b html docs docs\_build\html

El punto de entrada resultante es ``docs/_build/html/index.html``.
