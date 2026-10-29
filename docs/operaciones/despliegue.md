# Despliegue y operación

Componente 06 de la guía. Responsable sugerido: infraestructura junto con desarrollo. Actualizar cuando cambien infraestructura o procedimientos; verificar en cada release.

Revisión: 29/10/2026. La [guía de VPS Ubuntu](../DESPLIEGUE_VPS.md) es el procedimiento vigente e incluye Caddy, unidades systemd, dependencias fijadas y verificación de configuración. Este documento conserva el contexto operativo; el despliegue, rollback y restauración requieren ensayo en el servidor real.

## Ambientes y configuración

Desarrollo: SQLite permitido, `DEBUG=true`, Django 8000, FastAPI externo 8001 y Redis 6379 según plantilla. Staging/producción: PostgreSQL, `DEBUG=false`, dominio permitido, secretos propios, TLS y proxy con soporte WebSocket. No copiar datos personales a pruebas.

Partir de `.env.example`. Grupos obligatorios: `SECRET_KEY`, `ALLOWED_HOSTS`, `DB_ENGINE=postgresql`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_SSLMODE`; integración `IA_API_URL`, `IA_OFFER_API_URL`, `IA_API_TOKEN`, `IA_CALLBACK_HMAC_SECRET`, `MATCH_API_URL`, `MATCH_API_HTTP_URL`, `MATCH_API_TOKEN`; Redis `CHANNEL_REDIS_URL`, `MATCH_CACHE_REDIS_URL`; seguridad `CSRF_TRUSTED_ORIGINS`, `TRUST_PROXY_HEADERS`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`; correo opcional `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` y contacto `IEN_CONTACT_EMAIL`.

Los tokens salientes deben coincidir con la configuración de servicio de FastAPI y el secreto HMAC con el de callbacks. `IA_CALLBACK_URL` está reservada y no se usa en el flujo actual. `MATCH_CACHE_TTL_SECONDS` predetermina 604800 s y `MATCH_REQUESTS_PER_HOUR` 20; son parámetros técnicos, no política de retención de CV. No se requiere configurar un proveedor LLM en Django: corresponde al servicio externo.

## Arranque local de Django y despachadores

Seguir primero el `README.md` (raíz del repositorio) para entornos, migraciones, Redis, FastAPI y Celery. Además de la web, ejecutar estos dos procesos en terminales independientes:

```bash
.venv/bin/python manage.py run_integration_dispatcher --kind extraction --interval 2
.venv/bin/python manage.py run_integration_dispatcher --kind match --interval 2
```

Para una entrega acotada, sin bucle continuo:

```bash
.venv/bin/python manage.py dispatch_integration_outbox --once
.venv/bin/python manage.py dispatch_match_jobs --once
```

Estos comandos entregan trabajos reales del entorno configurado; no usarlos como comprobación de solo lectura en producción. Redis y workers Celery del servicio externo se inician en su propio repositorio. El servidor debe ser ASGI para notificaciones; `channels[daphne]` está declarado y también se puede iniciar explícitamente:

```bash
.venv/bin/daphne -b 127.0.0.1 -p 8000 ientrabajo.asgi:application
```

## Servicios productivos propuestos

Supervisar por separado web ASGI, dispatcher de extracción y dispatcher de match, además de PostgreSQL, Redis y el stack externo de IA. Definir usuario de servicio sin privilegios, directorio de trabajo, entorno privado, reinicio con backoff y logs por proceso. No se incluyeron unidades systemd porque aún no están definidos host, usuario ni rutas de instalación.

El proxy sirve estáticos/medios públicos, reenvía HTTP y Upgrade de WebSocket y bloquea `/media/postulantes/cv/` y `/media/ia/extraction_snapshots/`. Nunca publicar `private_uploads/`. Validar orígenes/CSRF y cabeceras de proxy; confiar en X-Forwarded-Proto solo desde un proxy controlado.

## Secuencia de despliegue propuesta

1. Identificar revisión de Django y versión compatible de FastAPI; ejecutar pruebas y revisión del plan de migraciones en staging.
2. Respaldar PostgreSQL, `private_uploads/` y `media/` en una ventana consistente; conservar configuración cifrada y referencias de release.
3. Detener entregas/escrituras para cambios incompatibles; instalar dependencias en un entorno de release. No ejecutar dos versiones incompatibles de dispatchers sobre la misma outbox.
4. Revisar y aplicar:

```bash
.venv/bin/python manage.py check --deploy
.venv/bin/python manage.py migrate --plan
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
```

5. Arrancar/reiniciar servicios supervisados y comprobar login, oferta, descarga privada, extracción de archivo sintético, callback y match. Verificar WebSocket y consulta HTTP de estado.
6. Registrar release, migraciones, resultados, pendientes y responsable. Habilitar tráfico completo después del smoke.

## Rollback propuesto

Detener web/dispatchers afectados y revisar si el código anterior es compatible con el esquema. Si lo es, restaurar la release previa y reiniciar. Si no lo es, usar únicamente una migración inversa ensayada o restaurar backup consistente de BD y archivos. Una restauración pierde escrituras posteriores al backup: acordar la ventana antes de realizarla. No ejecutar migraciones inversas ni borrar eventos automáticamente. Mantener colas/callbacks de versiones incompatibles aislados durante la recuperación.

## Backup y restauración

Ejemplo para PostgreSQL con credenciales mediante `.pgpass` o mecanismo de secretos, sin contraseña en comandos:

```bash
pg_dump --format=custom --file=bolsa-backup.dump --host=HOST --username=USUARIO BASE
pg_restore --dbname=BASE_RESTAURACION --host=HOST --username=USUARIO --no-owner bolsa-backup.dump
```

Sustituir HOST/USUARIO/BASE; `BASE_RESTAURACION` debe ser una base vacía y aislada. Respaldar también archivos de CV, snapshots e imágenes con acceso restringido. En SQLite local, detener escritores antes de copiar; no tratar una copia en caliente del archivo como respaldo consistente. Redis no reemplaza el backup relacional; la caché puede reconstruirse, pero la cola externa necesita su estrategia propia.

Ensayar restauración en ambiente aislado: verificar migraciones, conteos, integridad de relaciones, hashes/lectura de archivos y permisos de descarga. Medir y acordar RPO/RTO, frecuencia, cifrado, retención y responsable. Aún no hay una restauración productiva acreditada en esta entrega.

## Logs, métricas y recuperación

No hay un sistema central de observabilidad declarado. Capturar stdout/stderr de procesos y logs Django; incluir request_id/event_id y estado, evitando CV, JSON personales y tokens.

| Síntoma | Revisión / recuperación |
| --- | --- |
| Trabajo pendiente sin avanzar | Procesos de despacho, cantidad/antigüedad de EventoSalida pending/sending y proximo_intento_en; conectividad del servicio. |
| Envío incierto o reconexiones | Conservar clave de idempotencia; revisar lease y aceptación remota antes de reenviar manualmente. |
| Callback 401 | Secreto HMAC, bytes firmados y reloj sincronizado (ventana 300 s). |
| Match rate_limited | Cuota y espera del proveedor; mostrar estado al usuario y revisar cola externa; no duplicar trabajos para forzar la cuota. |
| No llegan avisos | ASGI, proxy Upgrade, Redis Channels, sesión/origen/token; probar consulta HTTP de estado. |
| Resultado anterior al CV actual | Versiones y hashes; analizar CV vigente, sin sobrescribir historial. |
| CV heredado público | Bloquear ruta en proxy; respaldar y ejecutar primero `manage.py migrar_cv_privados` en revisión. `--apply` mueve archivos y requiere ventana controlada. |
| PostgreSQL no conecta | Credenciales privadas, red, TLS y DB_ENGINE; comprobar protecciones con tests de configuración. |

Proponer alertas por antigüedad de outbox, errores de callback/servicio y espacio disponible. Umbrales y guardia aún deben acordarse. No se configuraron alarmas ni tareas programadas en esta entrega.
