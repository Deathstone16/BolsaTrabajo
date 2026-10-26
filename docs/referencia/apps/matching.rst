Compatibilidad y recomendaciones de cursos
==========================================

La app ``matching`` calcula una compatibilidad entre un perfil canónico de
postulante y el perfil extraído de una oferta. El request web sólo crea o
recupera una ejecución persistida; la llamada al proveedor externo se hace en
segundo plano desde el outbox compartido de ``ia``.

Precondiciones y snapshots
--------------------------

Para calcular, el perfil de postulante debe estar listo, corresponder al CV
actual y usar ``candidate-profile.v2``. La oferta debe tener requisitos sin
revisión pendiente, perfil listo en ``job-offer.v2`` y un trabajo de extracción
completado cuyo hash corresponda a la oferta actual. Se requiere una
configuración de compatibilidad publicada. Sus siete pesos (competencias
técnicas, habilidades blandas, experiencia, educación, idiomas, logística y
requisitos deseables) deben sumar 100%; las configuraciones publicadas son
inmutables.

Cada ``ResultadoCompatibilidad`` conserva snapshots de ambos perfiles, sus
versiones y hashes, configuración y pesos, rúbrica, versión de prompt, fecha de
evaluación, proveedor/modelo y claves de caché. La clave incorpora esas entradas,
por lo que un cambio relevante genera otra ejecución. Redis guarda resultados
por clave con TTL y limita nuevas solicitudes por postulante por hora; si Redis
falla, el caché y el limitador se omiten para que la ejecución persistida pueda
continuar. Repetir una clave existente no consume una nueva solicitud.

Integración con el matcher
--------------------------

``dispatch_match_jobs`` reclama un evento ``match`` pendiente con lock y lease,
y se conecta a ``MATCH_API_URL`` mediante WebSocket de servidor a servidor con
``Authorization: Bearer MATCH_API_TOKEN``. Envía un JSON con tipo
``match.start`` y ``payload`` serializado según el contrato ``match.v2``:
perfiles, metadatos (hashes/versiones, rúbrica, prompt, modelo y fecha) y
configuración de pesos.

El dispatcher acepta mensajes de estado ``accepted``, ``processing`` y
``rate_limited``; un mensaje ``match.completed`` debe incluir ``result``. Django
valida ``match-result.v2``, el request ID, la configuración solicitada, el
estado obligatorio, cada requisito contra el snapshot de oferta y la suma de
puntos antes de guardar el resultado. Un mensaje fallido deja el match en error.
Ante errores de transporte, el evento vuelve a pendiente con reintento
exponencial limitado. El estado y el resultado quedan persistidos localmente.

El payload de estado HTTP/WebSocket incluye ``request_id``, ``status``,
``match_percentage``, ``coverage_percentage``, ``confidence_percentage``,
``result`` (sólo completado), ``error``, hash/configuración de pesos, fecha de
evaluación y versiones de modelo. En el protocolo actual la confianza
cuantificada no está disponible: el resultado v2 exige
``confidence_available: false`` y ``confidence_percentage: null``.

Rutas y notificaciones
----------------------

Las rutas HTTP (bajo el prefijo del proyecto) son:

* ``ofertas/<oferta_id>/calcular/``: POST autenticado de postulante; devuelve
  HTTP 202 mientras la ejecución no esté completada y 200 si ya lo está. Las
  precondiciones o el límite de solicitudes se informan como 409.
* ``estado/<request_id>/``: GET de estado, restringido al postulante propietario.
* ``resultado/<request_id>/``: GET del detalle autorizado, con evaluaciones
  obligatorias/deseables, desglose por dimensión y sugerencias de cursos.

El WebSocket ``ws/matches/<request_id>/`` exige usuario autenticado y que el
match pertenezca a ese usuario. Al conectarse se une a ``match-<request_id>`` y
recibe el estado actual; después recibe eventos ``match.update`` convertidos a
JSON de estado. ``Channels`` propaga estas notificaciones; Redis puede servir
como backend de Channels según la configuración del proyecto. Si la notificación
falla, el estado HTTP lee el resultado persistido.

Recomendaciones del catálogo
----------------------------

Las recomendaciones son de sólo lectura y se calculan al mostrar un match
completado. Se derivan de los requisitos y evaluaciones congelados en el
snapshot del match, y consultan el catálogo actual de cursos activos. Sólo se
consideran brechas ``not_met``, ``partial`` o ``unknown`` de competencias
técnicas, habilidades blandas, idiomas y requisitos deseables. Se excluyen
títulos/licencias, educación formal, experiencia y requisitos con años mínimos
positivos; tampoco se reemplaza un requisito guardado por los campos actuales
de la oferta.

La coincidencia específica se ordena por mención en título, habilidad asociada
en el catálogo y mención en descripción. Si no hay coincidencias específicas,
puede sugerirse un curso general de la misma categoría de la oferta. Se devuelven
hasta tres cursos por brecha y seis tarjetas únicas. Los textos explican la
evidencia del catálogo; una sugerencia general pide revisar el temario. Estas
referencias no afirman que el curso otorgue un título, licencia o experiencia,
ni cambian el resultado del match. Si no hay brechas entrenables no se muestran
sugerencias; ``no_catalog`` distingue la ausencia de cursos activos.

.. automodule:: matching.configuration
   :members:

.. automodule:: matching.services
   :members:

.. automodule:: matching.course_recommendations
   :members:

.. automodule:: matching.views
   :members:

.. automodule:: matching.models
   :members:
