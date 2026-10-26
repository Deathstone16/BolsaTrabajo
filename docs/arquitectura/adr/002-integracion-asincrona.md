# ADR-002: integración asíncrona con outbox e idempotencia

Fecha: 22/10/2026. Estado: decisión observada en la implementación.

**Contexto.** Una inferencia puede exceder la duración admisible de una petición, fallar o ser aceptada antes de perder la conexión. Reintentar sin identidad estable puede duplicar trabajo y costo.

**Decisión.** Guardar el trabajo y `EventoSalida` en base relacional, enviarlos desde comandos independientes, usar claves de idempotencia y deduplicar callbacks con `EventoRecepcion.event_id`. Extracción usa HTTP y callback HMAC; matching usa WebSocket autenticado y HTTP para cancelar. El navegador consulta/escucha a Django.

**Consecuencias.** La entrega admite reintentos y los consumidores deben ser idempotentes; no se promete ejecución exactamente una vez. Se necesitan supervisión de dispatchers, manejo de leases, monitoreo de antigüedad de pendientes y validación de respuestas tardías. El WebSocket de match mantiene una conexión por trabajo mientras lo atiende el dispatcher.

**Alternativa.** Una llamada LLM síncrona desde la vista alarga la petición y dificulta recuperación. Una cola propia de Django sería otra arquitectura, no la implementada.

Fuentes: `ia/workflow.py`, `ia/management/commands/dispatch_integration_outbox.py`, `matching/management/commands/dispatch_match_jobs.py`, `matching/services.py`.
