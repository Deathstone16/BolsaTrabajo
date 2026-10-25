Arquitectura
============

La solución integra dos servicios Python 3.11. BolsaTrabajo usa Django con el
patrón MVT para la aplicación web y sus casos de uso; el repositorio
``ia_api/backend`` expone FastAPI para extracción y análisis asistidos por
modelos. PostgreSQL
almacena los datos de negocio en producción y Redis coordina tareas, resultados,
notificaciones y cachés. Django usa SQLite como opción de desarrollo.

Componentes
-----------

Django
   Gestiona autenticación, postulantes, oferentes, ofertas, cursos,
   moderación, versiones de CV, perfiles profesionales y resultados de match.
   Sus apps se organizan en ``apps/``; ``models.py``, ``forms.py``,
   ``services.py`` y ``views.py`` separan persistencia, validación, casos de
   uso y coordinación HTTP. Daphne sirve la aplicación ASGI y Django Channels
   publica notificaciones en tiempo real mediante Redis.

FastAPI
   Expone endpoints versionados para análisis de CV, ofertas, normalización de
   perfiles y match. Pydantic valida los contratos. La extracción de PDF,
   consolidación y llamadas a proveedores se implementan en servicios de
   ``app/services/``; las tareas largas se ejecutan en workers Celery.

PostgreSQL y Redis
   PostgreSQL es la base de datos de negocio de Django. Redis funciona como
   broker y backend de resultados para Celery, almacén de trabajos y soporte
   de Channels, además de respaldar cachés. La API puede usar un catálogo
   PostgreSQL vectorial opcional para recuperar contexto semántico de
   habilidades; sin él dispone de un catálogo JSON local.

Workers y despachadores
   La API encola trabajos de extracción y matching en Celery. En Django,
   ``dispatch_integration_outbox`` entrega trabajos de CV, ofertas y
   normalización; ``dispatch_match_jobs`` entrega trabajos de compatibilidad.
   La bandeja de salida y las claves idempotentes permiten reintentar entregas
   sin depender de una llamada externa dentro de la transacción web.

Flujo de datos: CV, perfil, match y cursos
--------------------------------------------

1. El CV se recibe en Django y se valida antes de persistirlo en almacenamiento
   privado. Se aplican límites de carga y, cuando está habilitado, análisis
   antimalware. Cada reemplazo crea una versión para asociar los resultados con
   el documento que los originó.
2. Django registra un trabajo y un evento de salida, y el despachador envía el
   snapshot privado a FastAPI con token de servicio e identificador idempotente.
   FastAPI procesa la extracción en Celery y notifica el resultado a Django por
   callback. El callback se autentica con HMAC y se vincula al trabajo y a la
   versión del CV.
3. Durante la extracción, la API puede recuperar contexto del catálogo de
   habilidades para interpretar conceptos citados en el CV. Django persiste el
   perfil estructurado y deja los datos disponibles para que el postulante los
   revise y edite.
4. Para matching, Django entrega snapshots del perfil y de la oferta. FastAPI
   compara requisitos con evidencia del perfil mediante el proveedor
   configurado; la cola, el despachador y el callback permiten procesar el
   resultado de forma asíncrona. Los snapshots fijan los datos usados en esa
   evaluación.
5. En un match completado, Django identifica brechas que pueden abordarse con
   formación y consulta cursos activos. Prioriza coincidencias explícitas en
   título, habilidades vinculadas o descripción, y puede sugerir cursos
   generales del área. La recomendación es de solo lectura y no altera el
   resultado de compatibilidad.

Seguridad y operación
---------------------

* Los secretos, tokens de servicio y clave HMAC se configuran en el entorno,
  nunca en el código. Las llamadas internas usan Bearer y comparaciones de
  token resistentes a diferencias de tiempo; los callbacks verifican HMAC.
* Los CV se almacenan en rutas privadas y no deben servirse como archivos
  estáticos o medios públicos. Las cargas tienen límites y pueden exigir
  escaneo antimalware. La API rechaza cargas no autenticadas o sobredimensionadas
  antes de procesar el multipart.
* En producción Django requiere ``DEBUG=False``, ``SECRET_KEY`` y
  ``ALLOWED_HOSTS`` explícitos, PostgreSQL y conexión TLS para hosts TCP. Las
  cookies de sesión y CSRF son seguras; HTTPS, CSRF y orígenes confiables deben
  configurarse de acuerdo con el proxy.
* Daphne y FastAPI deben quedar detrás de un proxy confiable. Solo se confía en
  ``X-Forwarded-Proto`` cuando el proxy controlado lo establece. Caddy puede
  servir recursos públicos y denegar el resto de ``/media/``; Cloudflare Tunnel
  publica el origen sin exponer directamente los puertos de aplicación.
* Redis, PostgreSQL, la API y los workers no deben quedar expuestos a Internet.
  Para el despliegue, migración de datos, proxy y túnel, consultá
  :doc:`DESPLIEGUE_VPS <DESPLIEGUE_VPS>`.

Dependencias
------------

Las dependencias de runtime de Django están en ``requirements.txt``. La API
mantiene su propio ``requirements.txt`` bajo ``backend``. Las herramientas
Sphinx para esta documentación se declaran en ``requirements-dev.txt``.
