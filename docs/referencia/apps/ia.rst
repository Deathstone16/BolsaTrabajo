Procesamiento con IA
====================

El módulo ``ia`` conserva los CV aceptados, solicita su extracción al servicio
externo y publica perfiles canónicos validados. La generación de perfiles no se
ejecuta dentro del request web: el flujo persiste trabajos y eventos de salida,
y un dispatcher los entrega a la API externa.

Modelos y versiones
-------------------

``CVVersion`` identifica una versión inmutable del CV aceptado, con nombre,
formato, tamaño y SHA-256. El archivo se guarda mediante ``PrivateCVStorage``
fuera del árbol servido como ``MEDIA_URL``; su método ``url`` impide generar una
URL pública. ``AnalisisCV`` registra la solicitud y la respuesta histórica para
una versión. ``PerfilCV`` es el perfil editable y canónico actual del postulante;
``VersionPerfilCV`` conserva sus publicaciones versionadas. Para ofertas,
``PerfilOferta`` y ``VersionPerfilOferta`` guardan el perfil extraído y su
historial. Los esquemas de contenido validados son ``candidate-profile.v2`` y
``job-offer.v2``.

``TrabajoExtraccion`` guarda el tipo de trabajo, clave de idempotencia, hash de
origen, versión de prompt, estado y, cuando corresponde, snapshot privado del
CV o snapshot del perfil. ``EventoSalida`` es el outbox que permite despachar
sin bloquear el request; ``EventoRecepcion`` registra ``event_id`` para evitar
aplicar callbacks duplicados. Los estados locales del trabajo incluyen
``pending``, ``sending``, ``accepted``, ``processing``, ``completed``, ``error``
y ``delivery_unknown``. Un callback tardío sólo publica perfiles cuando sigue
correspondiendo a la versión actual del CV o de la oferta.

Flujo de extracción
-------------------

La vista ``solicitar_analisis`` requiere autenticación, rol de postulante y un
CV versionado. Si ``IA_API_URL`` no está configurada responde 503. En caso
válido crea o recupera análisis/trabajo idempotente y devuelve HTTP 202 con
``success``, ``mensaje``, ``analisis_id`` y ``version_cv_id``. Un CV pendiente
de la misma versión y prompt se reutiliza; también se reutiliza el análisis
completado vigente.

El comando ``dispatch_integration_outbox`` reclama eventos elegibles bajo lock
y lease, y entrega los trabajos según su tipo:

* CV: POST multipart a ``IA_API_URL`` con ``Authorization: Bearer …``,
  ``Idempotency-Key`` y campos ``analysis_id``, ``candidate_id``, ``user_id``
  y ``cv_version_id``, además del archivo ``cv`` tomado del snapshot privado.
* Oferta: POST JSON a ``IA_OFFER_API_URL`` o, si no se configuró, a la ruta
  derivada reemplazando ``/cv-analyses`` por ``/offer-analyses``. El cuerpo
  lleva ``offer_id``, ``source_hash`` y ``offer_snapshot``.
* Normalización de edición: POST JSON a la ruta derivada con
  ``candidate_id``, ``source_hash`` y ``profile_snapshot``.

Las tres solicitudes usan token Bearer e idempotency key y esperan una respuesta
HTTP exitosa con ``job_id``. Los fallos de entrega dejan el evento pendiente
con reintento exponencial limitado; una aceptación registra el identificador
remoto y marca el outbox como enviado. El worker externo procesa el trabajo de
forma asíncrona.

La API externa devuelve el resultado a ``llegue`` por POST. El callback requiere
``X-IA-Event-Timestamp`` y ``X-IA-Callback-Signature``; la firma es HMAC-SHA256
del texto ``timestamp + '.' + cuerpo`` con ``IA_CALLBACK_HMAC_SECRET`` y la
marca temporal debe estar dentro de 300 segundos. El JSON debe incluir
``event_id``, ``request_id`` y ``source_hash``. Django comprueba la identidad y
el tipo del trabajo, el hash y los propietarios/versiones, valida el perfil
contra los contratos compartidos y aplica cada evento una sola vez. Un callback
duplicado devuelve ``success: true`` y ``duplicado: true``; uno inválido se
rechaza.

Cuando el callback afecta un análisis de CV, Django emite una notificación al
grupo ``user_<id>``. El consumer de ``ws/cv-analysis/`` comprueba sesión y token
firmado de un solo usuario (máximo 1 hora) y envía ``{"type": "cv.analyzed",
"payload": …}``. El payload indica ``analysis_id``, ``version_cv_id``, si esa
versión sigue vigente, ``status``, mensaje y, sólo para el resultado vigente,
``resultado_url``. La vista HTTP de estado sigue disponible como alternativa y
no sustituye la autorización por propietario.

Rutas HTTP
----------

Las rutas de esta app (bajo el prefijo que configure el proyecto) son:

* ``solicitar-analisis/``: POST para iniciar o recuperar la extracción.
* ``analisis/<analisis_id>/estado/``: consulta de estado del análisis propio;
  informa si pertenece a una versión anterior y la URL de resultado cuando
  está listo.
* ``analisis/<analisis_id>/``: muestra el resultado autorizado.
* ``analisis/<analisis_id>/habilidades/``: edición de habilidades del análisis.
* ``perfil-profesional/`` y ``perfil-cv/editar/``: perfil profesional y edición
  del perfil canónico.
* ``llegue/``: callback firmado del servicio externo.

.. automodule:: ia.workflow
   :members:

.. automodule:: ia.views
   :members:

.. automodule:: ia.models
   :members:
