# Contratos HTTP y WebSocket

Componente 04 de la guía. Responsable sugerido: desarrolladores que mantienen los contratos. Actualizar cuando cambie cualquier contrato o comportamiento observable.

Revisión: 22/10/2026. Contratos observados en Django; no se generó ni verificó el OpenAPI de FastAPI. En un entorno con el microservicio, consultar `/docs` y `/openapi.json` si su configuración los habilita. No hay un endpoint OpenAPI propio de Django en este repositorio.

## Interfaz Django

Las rutas de usuario requieren sesión del postulante. Los POST de navegador requieren CSRF. Una sesión ausente puede redirigir al login (302); los fallos de CSRF/permisos pueden producir HTML 403 y un método no permitido 405. No se debe asumir que todos los errores son JSON.

| Método y ruta | Entrada | Respuesta y errores específicos |
| --- | --- | --- |
| POST `/ia/solicitar-analisis/` | Sin cuerpo de negocio; usa el CV actual de la sesión. | 202: `success`, `mensaje`, `analisis_id`, `version_cv_id`; 400 sin CV, 409 conflicto, 502 fallo al preparar archivo, 503 sin servicio configurado. |
| GET `/ia/analisis/{id}/estado/` | ID entero, análisis propio. | 200: `estado`, `version_cv_id`, `es_version_actual`, `mensaje`, `resultado_url`; 404 ajeno/inexistente. |
| GET `/ia/analisis/{id}/` | Análisis propio. | HTML de resultado, con controles de vigencia; 404 ajeno/inexistente. |
| POST `/matching/ofertas/{id}/calcular/` | ID de oferta activa, sin cuerpo de negocio. | 202 pendiente o 200 completado; `success`, `created` y estado de match; 409 perfil/configuración no aptos; 404 oferta ausente o no activa. |
| GET `/matching/estado/{uuid}/` | UUID propio. | 200: estado de match; 404 ajeno/inexistente. |
| POST `/matching/cancelar/{uuid}/` | UUID propio. | 200: `success` y estado; 404 ajeno/inexistente. |
| GET `/matching/resultado/{uuid}/` | UUID propio. | HTML con detalle, requisitos, desglose y cursos; 404 ajeno/inexistente. |
| GET `/usuarios/cv/{version_id}/descargar/` | Versión entera propia. | Archivo privado bajo autorización; no usar URL directa del FileField. |

`estado_analisis` no tiene decorador que limite exclusivamente a GET; se documenta GET como uso del cliente. Las vistas de edición de perfil/habilidades emplean formularios HTML, no constituyen una API JSON pública.

### Esquema de estado de compatibilidad

`request_id` UUID; `status` en pending, processing, rate_limited, completed, error, cancelled; porcentajes numéricos o null; `result` objeto solo si completado; `error` texto o null; `scoring_config_hash` texto; `scoring_config` versión y pesos o null; `evaluation_date` ISO o null; `model_version`, `provider_model_config` textos; `confidence_available` booleano. No se muestra una confianza cuantificada cuando el protocolo no la entrega.

Ejemplo parcial de solicitud encolada (los campos restantes siguen el esquema anterior):

```json
{"success": true, "created": true, "request_id": "3e13b5cb-3780-4b4e-aee6-1804f6825827", "status": "pending", "match_percentage": null, "result": null}
```

Ejemplo desde un navegador con sesión y CSRF disponibles:

```javascript
fetch('/matching/ofertas/42/calcular/', {
  method: 'POST',
  headers: {'X-CSRFToken': csrfToken},
  credentials: 'same-origin'
});
```

## Django hacia el servicio de IA

No entregar tokens de servicio al navegador. Las URL son configurables; los siguientes son los paths de la plantilla local.

| Transporte / ruta | Cabeceras y contenido | Expectativa del consumidor |
| --- | --- | --- |
| POST `/api/v1/cv-analyses` | Bearer `IA_API_TOKEN`; `Idempotency-Key`; multipart `cv`, `analysis_id`, `candidate_id`, `user_id`, `cv_version_id`. | HTTP exitoso con JSON que contiene `job_id`. Django conserva el snapshot privado. |
| POST `/api/v1/offer-analyses` | Mismo Bearer/idempotencia; JSON `offer_id`, `source_hash`, `offer_snapshot`. | JSON con `job_id`. |
| POST `/api/v1/profile-normalizations` | Mismo Bearer/idempotencia; JSON `candidate_id`, `source_hash`, `profile_snapshot`. | JSON con `job_id`. |
| WS `/api/v1/ws/v1/matches` | Bearer `MATCH_API_TOKEN`; evento `match.start` con `payload` MatchRequest. | Estados accepted, processing, rate_limited, completed o failed. completed incluye `result`; failed puede incluir `error`. |
| POST `/api/v1/matches/{request_id}/cancel` | Bearer `MATCH_API_TOKEN`. | HTTP exitoso; se reintenta si no pudo entregarse. |

Extracción usa timeout HTTP de 20 segundos; la espera larga ocurre fuera de la vista web. Matching abre el socket con timeout de conexión de 10 segundos y consulta recepción periódicamente. Los reintentos conservan identidad del trabajo y usan espera creciente con tope según comando.

## Callback de extracción

`POST /ia/llegue/`, exento de CSRF y sin sesión de usuario; autenticado por HMAC. Cabeceras `X-IA-Event-Timestamp` (segundos Unix) y `X-IA-Callback-Signature` (hex SHA-256). Firma sobre bytes exactos: `timestamp + b'.' + cuerpo`, con `IA_CALLBACK_HMAC_SECRET`. Ventana temporal: diferencia absoluta máxima de 300 segundos.

El cuerpo debe incluir `event_id`, `request_id` (clave de idempotencia de TrabajoExtraccion, no asumir que es su UUID), `source_hash` y el estado/contenido correspondiente. El workflow valida además kind, identificadores de candidato/análisis/oferta y job remoto cuando corresponde. CV: kind candidate_cv; oferta: job_offer; normalización: profile_normalization. Completado exige `result` compatible con el perfil. No reutilizar solo un ejemplo mínimo como payload válido.

Respuestas: 200 `{ "success": true, "duplicado": false }` o duplicado true; 401 firma/timestamp inválido o vencido; 400 JSON inválido o sin claves básicas; 404 solicitud inexistente/incompatible; 405 método distinto de POST. La validación exhaustiva de payload malformado debe cubrirse con tests de integración.

## Eventos hacia el navegador

| URL | Autenticación | Mensajes |
| --- | --- | --- |
| `/ws/matches/{uuid}/` | Sesión y propiedad del resultado; origen permitido. | Estado inicial y actualizaciones con el mismo esquema de `status_payload`. Cierre 4401 anónimo, 4404 ajeno/inexistente. |
| `/ws/cv-analysis/?token=...` | Sesión + token Django firmado, salt `ia.cv-analysis.websocket`, duración máxima 3600 s y usuario coincidente. | Envelope `type: cv.analyzed`, `payload` de notificación. Cierre 4401 si no autoriza. |
| `/ws/cv/` | Sesión autenticada; grupo privado de usuario. | Payload directo de notificación, sin el envelope anterior. |

La notificación CV puede incluir `analysis_id`, `version_cv_id`, `es_version_actual`, `status`, `mensaje` y `resultado_url`. Los dos canales CV tienen formatos diferentes y no deben intercambiarse en el cliente. HTTP de estado permite recuperar el resultado si se interrumpe la conexión.

## Versionado y reglas del contenido

`ien_contracts/models.py` es la fuente verificable de CandidateProfile, JobOffer, MatchRequest y MatchResult. Admite perfiles v1/v2; el flujo de matching construye `match.v2`, perfiles `candidate-profile.v2` y `job-offer.v2`, pesos para exactamente siete dimensiones y suma 10000 basis points. Los requisitos llevan ID único, categoría y obligatoriedad explícita; los deseables no pueden ser obligatorios. Se conserva fecha de evaluación para credenciales. Los JSON persistidos no crean tablas por cada habilidad o experiencia.

Antes de una integración, comparar esquemas Pydantic con el OpenAPI externo y probar autenticación, idempotencia, callback firmado, errores, cancelación y resultado tardío. No cambiar enums o unidades sin ajustar consumidores y tests.
